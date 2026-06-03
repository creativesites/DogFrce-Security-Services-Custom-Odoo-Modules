from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import date, datetime


class TestSecurityPayroll(TransactionCase):

    def setUp(self):
        super().setUp()

        # Get default Namibian Rule Set
        self.rule_set = self.env["security.payroll.rule.set"].search(
            [("country_code", "=", "NA")], limit=1
        )
        if not self.rule_set:
            # Fallback creation if not pre-loaded (though data/security_l10n_na_data.xml defines it)
            self.rule_set = self.env["security.payroll.rule.set"].create({
                "name": "Test Namibia Rule Set",
                "country_code": "NA",
                "currency_id": self.env.ref("base.NAD").id,
                "effective_from": "2024-03-01",
                "employee_ssc_rate": 0.009,
                "employer_ssc_rate": 0.009,
                "ssc_salary_cap": 9000.0,
                "sunday_multiplier": 1.5,
                "public_holiday_multiplier": 1.5,
                "overtime_multiplier": 1.5,
            })

            # Recreate brackets
            self.env["security.tax.bracket"].create([
                {
                    "rule_set_id": self.rule_set.id,
                    "lower_bound": 0.0,
                    "upper_bound": 100000.0,
                    "fixed_amount": 0.0,
                    "rate": 0.00,
                },
                {
                    "rule_set_id": self.rule_set.id,
                    "lower_bound": 100000.01,
                    "upper_bound": 150000.0,
                    "fixed_amount": 0.0,
                    "rate": 0.18,
                },
                {
                    "rule_set_id": self.rule_set.id,
                    "lower_bound": 150000.01,
                    "upper_bound": 1500000.0,
                    "fixed_amount": 9000.0,
                    "rate": 0.25,
                }
            ])

        # Create Client, Site, Post type, Post and Shift Template for attendance logs
        self.client = self.env["res.partner"].create({"name": "Windhoek Mall"})
        self.site = self.env["security.client.site"].create({
            "name": "Main Site",
            "partner_id": self.client.id,
        })
        self.post_type = self.env["security.post.type"].create({"name": "Security Guard Post"})
        self.post = self.env["security.post"].create({
            "name": "Main Entrance",
            "partner_id": self.client.id,
            "site_id": self.site.id,
            "post_type_id": self.post_type.id,
        })
        self.shift_template = self.env["security.shift.template"].create({
            "name": "12-Hour Shift",
            "start_hour": 6.0,
            "end_hour": 18.0,
        })

        # Create test guards with different rates
        self.guard_low = self.env["hr.employee"].create({
            "name": "Low-Income Guard",
            "security_guard": True,
            "security_hourly_rate": 10.0, # Will earn ~120 NAD per 12h shift
            "security_ssc_number": "SSC-111",
            "security_tax_number": "TAX-111",
        })

        self.guard_high = self.env["hr.employee"].create({
            "name": "High-Income Officer",
            "security_guard": True,
            "security_hourly_rate": 50.0, # Will earn ~600 NAD per 12h shift
            "security_ssc_number": "SSC-999",
            "security_tax_number": "TAX-999",
        })

        # Create Payroll Period
        self.period = self.env["security.payroll.period"].create({
            "name": "May 2026 Run",
            "date_from": "2026-05-01",
            "date_to": "2026-05-31",
            "rule_set_id": self.rule_set.id,
        })

    def test_01_low_income_payslip_calculations(self):
        """Under the N$ 100k/year (N$ 8,333.33/month) threshold, PAYE is 0, basic SSC applies."""
        # John worked 20 shifts of 12 hours (240 hours) at N$ 10/hour = N$ 2,400.00
        for i in range(1, 21):
            slot = self.env["security.roster.slot"].create({
                "shift_date": f"2026-05-{i:02d}",
                "post_id": self.post.id,
                "shift_template_id": self.shift_template.id,
                "employee_id": self.guard_low.id,
            })
            self.env["security.attendance.record"].create({
                "roster_slot_id": slot.id,
                "check_in": f"2026-05-{i:02d} 06:00:00",
                "check_out": f"2026-05-{i:02d} 18:00:00",
            })

        self.period.action_generate_payslips()
        
        payslip = self.env["security.payslip"].search([
            ("period_id", "=", self.period.id),
            ("employee_id", "=", self.guard_low.id)
        ])
        self.assertTrue(payslip, "Payslip should be generated.")
        
        # Total Earnings = 240 hours * N$ 10.0 = N$ 2400.0
        self.assertAlmostEqual(payslip.total_earnings, 2400.0)
        
        # SSC = 0.009 * 2400 = N$ 21.60
        ssc_line = payslip.deduction_line_ids.filtered(lambda l: l.code == "SSC")
        self.assertTrue(ssc_line, "SSC deduction line must exist.")
        self.assertAlmostEqual(ssc_line.amount, 21.60)
        
        # PAYE = 0.0
        paye_line = payslip.deduction_line_ids.filtered(lambda l: l.code == "PAYE")
        self.assertFalse(paye_line, "Should not pay PAYE below the tax threshold.")
        
        # Net Pay = 2400 - 21.60 = 2378.40
        self.assertAlmostEqual(payslip.net_pay, 2378.40)

    def test_02_high_income_payslip_calculations_and_ssc_cap(self):
        """Above basic limits: PAYE applies based on brackets, SSC is capped at N$ 81.00."""
        # High guard worked 20 shifts of 12 hours (240 hours) at N$ 50/hour = N$ 12,000.00
        for i in range(1, 21):
            slot = self.env["security.roster.slot"].create({
                "shift_date": f"2026-05-{i:02d}",
                "post_id": self.post.id,
                "shift_template_id": self.shift_template.id,
                "employee_id": self.guard_high.id,
            })
            self.env["security.attendance.record"].create({
                "roster_slot_id": slot.id,
                "check_in": f"2026-05-{i:02d} 06:00:00",
                "check_out": f"2026-05-{i:02d} 18:00:00",
            })

        self.period.action_generate_payslips()
        
        payslip = self.env["security.payslip"].search([
            ("period_id", "=", self.period.id),
            ("employee_id", "=", self.guard_high.id)
        ])
        self.assertTrue(payslip, "Payslip should be generated.")
        
        # Total Earnings = 240 hours * N$ 50.0 = N$ 12000.0
        self.assertAlmostEqual(payslip.total_earnings, 12000.0)
        
        # SSC = 0.009 * basic (12000) capped at 9000 -> 9000 * 0.009 = N$ 81.00
        ssc_line = payslip.deduction_line_ids.filtered(lambda l: l.code == "SSC")
        self.assertTrue(ssc_line)
        self.assertAlmostEqual(ssc_line.amount, 81.00)
        
        # PAYE calculation:
        # Taxable Monthly = 12000 - 81 = 11919.0
        # Annual Taxable = 11919.0 * 12 = 143028.0
        # Bracket 2 applies: 100k to 150k @ 18%
        # Annual PAYE = (143028 - 100000) * 0.18 = 7745.04
        # Monthly PAYE = 7745.04 / 12 = N$ 645.42
        paye_line = payslip.deduction_line_ids.filtered(lambda l: l.code == "PAYE")
        self.assertTrue(paye_line, "PAYE deduction line must exist.")
        self.assertAlmostEqual(paye_line.amount, 645.42)
        
        # Net Pay = 12000.0 - 81.00 - 645.42 = 11273.58
        self.assertAlmostEqual(payslip.net_pay, 11273.58)

    def test_03_period_workflow_and_totals(self):
        """Test confirming period updates totals, prints and closes."""
        # Setup one shift for low income guard
        slot = self.env["security.roster.slot"].create({
            "shift_date": "2026-05-01",
            "post_id": self.post.id,
            "shift_template_id": self.shift_template.id,
            "employee_id": self.guard_low.id,
        })
        self.env["security.attendance.record"].create({
            "roster_slot_id": slot.id,
            "check_in": "2026-05-01 06:00:00",
            "check_out": "2026-05-01 18:00:00",
        })

        self.assertEqual(self.period.state, "draft")
        self.period.action_generate_payslips()
        self.assertEqual(self.period.state, "processed")

        # Check period totals are computed
        self.assertAlmostEqual(self.period.total_earnings, 120.0)
        self.assertAlmostEqual(self.period.total_deductions, 1.08) # 0.009 * 120 = 1.08
        self.assertAlmostEqual(self.period.total_net_pay, 118.92)

        # Print check
        print_action = self.period.action_print_payslips()
        self.assertEqual(print_action["type"], "ir.actions.report")
        
        # Close period
        self.period.action_close()
        self.assertEqual(self.period.state, "closed")
