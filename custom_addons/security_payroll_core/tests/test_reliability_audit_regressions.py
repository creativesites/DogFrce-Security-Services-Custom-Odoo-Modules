from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError
from datetime import date, datetime


@tagged('post_install', '-at_install')
class TestReliabilityAuditRegressions(TransactionCase):

    def setUp(self):
        super().setUp()
        self.env.user.tz = "UTC"
        if self.env.company.partner_id:
            self.env.company.partner_id.tz = "UTC"
        self.employee_val = self.env["hr.employee"].create({
            "name": "Audit Test Employee",
            "security_guard": True,
            "security_hourly_rate": 20.0,
            "security_ssc_number": "SSC-REG-111",
            "security_tax_number": "TAX-REG-111",
        })
        self.supervisor_val = self.env["hr.employee"].create({
            "name": "Audit Test Supervisor",
        })
        self.client_val = self.env["res.partner"].create({"name": "Audit Client"})
        self.site_val = self.env["security.client.site"].create({
            "name": "Audit Site",
            "partner_id": self.client_val.id,
            "supervisor_id": self.supervisor_val.id,
        })
        self.post_type_val = self.env["security.post.type"].create({
            "name": "Audit Post Type",
        })
        self.post_val = self.env["security.post"].create({
            "name": "Audit Post",
            "partner_id": self.client_val.id,
            "site_id": self.site_val.id,
            "post_type_id": self.post_type_val.id,
        })
        self.shift_template_val = self.env["security.shift.template"].create({
            "name": "Audit Shift",
            "start_hour": 8.0,
            "end_hour": 20.0,
        })

    def test_roster_double_booking_constraint(self):
        """Test that creating overlapping roster slots for same employee, template, date, and state raises ValidationError."""
        self.env["security.roster.slot"].create({
            "shift_date": "2026-08-01",
            "employee_id": self.employee_val.id,
            "shift_template_id": self.shift_template_val.id,
            "post_id": self.post_val.id,
            "state": "assigned",
        })
        with self.assertRaises(ValidationError):
            self.env["security.roster.slot"].create({
                "shift_date": "2026-08-01",
                "employee_id": self.employee_val.id,
                "shift_template_id": self.shift_template_val.id,
                "post_id": self.post_val.id,
                "state": "assigned",
            })

    def test_holiday_dynamic_recomputation_trigger(self):
        """Test that creating/deleting a holiday triggers modified() on matching shift_date attendance records."""
        slot = self.env["security.roster.slot"].create({
            "shift_date": "2026-11-15",
            "employee_id": self.employee_val.id,
            "shift_template_id": self.shift_template_val.id,
            "post_id": self.post_val.id,
            "state": "confirmed",
        })
        batch = self.env["security.attendance.batch"].create({
            "site_id": self.site_val.id,
            "attendance_date": "2026-11-15",
        })
        record = self.env["security.attendance.record"].create({
            "roster_slot_id": slot.id,
            "attendance_batch_id": batch.id,
        })
        self.assertFalse(record.is_public_holiday)

        holiday = self.env["security.public.holiday"].create({
            "name": "Test Holiday",
            "holiday_date": "2026-11-15",
            "country_code": "NA",
        })
        self.env.flush_all()
        self.assertTrue(record.is_public_holiday)

        holiday.unlink()
        self.env.flush_all()
        self.assertFalse(record.is_public_holiday)

    def test_loan_floor_capping_and_carry_forward(self):
        """Test that payslip floor capping correctly updates or deletes linked security.loan.deduction tracking records, and rolls carry-forwards over cleanly."""
        rule_set = self.env["security.payroll.rule.set"].create({
            "name": "Reg Test Rules",
            "country_code": "ZM",
            "currency_id": self.env.ref("base.ZMW").id,
            "deduction_floor_pct": 0.50,
        })
        period = self.env["security.payroll.period"].create({
            "name": "Run ZM",
            "date_from": "2026-06-01",
            "date_to": "2026-06-30",
            "rule_set_id": rule_set.id,
        })
        loan = self.env["security.employee.loan"].create({
            "employee_id": self.employee_val.id,
            "start_date": "2026-06-01",
            "installment_amount": 100.0,
            "repayment_months": 2,
            "principal_amount": 200.0,
            "state": "active",
        })
        loan.action_generate_schedule()
        self.assertEqual(len(loan.deduction_line_ids), 2)
        
        # Create roster slot and attendance to yield exactly 150.0 earnings (7.5 hours * 20.0 rate)
        shift_template_7_5h = self.env["security.shift.template"].create({
            "name": "7.5h Shift",
            "start_hour": 8.0,
            "end_hour": 15.5,
        })
        slot = self.env["security.roster.slot"].create({
            "shift_date": "2026-06-02",
            "post_id": self.post_val.id,
            "shift_template_id": shift_template_7_5h.id,
            "employee_id": self.employee_val.id,
        })
        self.env["security.attendance.record"].create({
            "roster_slot_id": slot.id,
            "check_in": "2026-06-02 08:00:00",
            "check_out": "2026-06-02 15:30:00",
        })

        payslip = self.env["security.payslip"].create({
            "period_id": period.id,
            "employee_id": self.employee_val.id,
        })
        payslip.action_compute_from_sources()
        self.assertEqual(payslip.total_earnings, 150.0)
        self.env.flush_all()
        self.assertEqual(payslip.total_deductions, 75.0)
        self.assertEqual(payslip.net_pay, 75.0)

        loan_ded = self.env["security.loan.deduction"].search([
            ("loan_id", "=", loan.id),
            ("payslip_id", "=", payslip.id),
        ])
        self.assertEqual(len(loan_ded), 1)
        self.assertEqual(loan_ded.amount, 75.0)
        self.assertTrue(loan_ded.capped)
        self.assertEqual(loan_ded.carry_forward_amount, 25.0)

        payslip.action_confirm()
        next_lines = loan.deduction_line_ids.filtered(lambda l: not l.payslip_id)
        self.assertEqual(len(next_lines), 2)
        self.assertIn(125.0, next_lines.mapped("amount"))
        self.assertIn(100.0, next_lines.mapped("amount"))
