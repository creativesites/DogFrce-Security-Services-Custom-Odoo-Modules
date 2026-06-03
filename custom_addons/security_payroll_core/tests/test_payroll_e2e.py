"""
Sprint K-1 · Full end-to-end payroll pipeline integration test.

Coverage:
  Rule Set → Guard → Roster Slot → Attendance (5 hour-bucket categories)
  → Payslip generation → Earnings computation → SSC deduction → Net Pay
  → Payslip state machine (draft → confirmed → paid)
"""

from odoo.tests.common import TransactionCase


class TestPayrollE2E(TransactionCase):
    """
    Full end-to-end payroll pipeline test:
    Rule Set → Guard → Roster Slot → Attendance (5 buckets) → Payslip → Deductions → Net Pay
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env

        # NAD currency
        cls.nad = env.ref("base.NAD", raise_if_not_found=False) or env.company.currency_id

        # Rule set with all multipliers
        cls.rule_set = env["security.payroll.rule.set"].create({
            "name": "Test Namibia Rules E2E",
            "country_code": "NA",
            "currency_id": cls.nad.id,
            "effective_from": "2026-01-01",
            "employee_ssc_rate": 0.009,
            "employer_ssc_rate": 0.009,
            "ssc_salary_cap": 9000.0,
            "sunday_multiplier": 1.5,
            "public_holiday_multiplier": 1.5,
            "saturday_multiplier": 1.25,
            "night_shift_multiplier": 1.1,
            "overtime_multiplier": 1.5,
            "vat_rate": 15.0,
        })

        # PAYE bracket: 0% below 100,000 NAD/year
        env["security.tax.bracket"].create({
            "rule_set_id": cls.rule_set.id,
            "lower_bound": 0.0,
            "upper_bound": 100000.0,
            "fixed_amount": 0.0,
            "rate": 0.0,
        })

        # Grade
        cls.grade_a = env["security.grade"].create({
            "name": "Grade A E2E",
            "code": "A_E2E",
            "hourly_rate": 15.0,
        })

        # Guard employee — hourly rate comes from grade
        cls.guard = env["hr.employee"].create({
            "name": "Test Guard E2E",
            "security_guard": True,
            "security_grade_id": cls.grade_a.id,
            "security_ssc_number": "SSC999E2E",
            "security_tax_number": "TAX999E2E",
        })

        # Site / post / post-type infrastructure
        cls.partner = env["res.partner"].create({"name": "Test Client E2E", "is_company": True})
        cls.site = env["security.client.site"].create({
            "name": "Test Site E2E",
            "partner_id": cls.partner.id,
        })
        cls.post_type = env["security.post.type"].create({"name": "E2E Post Type"})
        cls.post = env["security.post"].create({
            "name": "E2E Main Gate",
            "site_id": cls.site.id,
            "post_type_id": cls.post_type.id,
            "partner_id": cls.partner.id,
        })

        # Shift templates
        cls.day_shift = env["security.shift.template"].create({
            "name": "Day Shift 06-14 E2E",
            "start_hour": 6.0,
            "end_hour": 14.0,
        })
        cls.night_shift_template = env["security.shift.template"].create({
            "name": "Night Shift 22-06 E2E",
            "start_hour": 22.0,
            "end_hour": 6.0,
        })

        # Payroll period (May 2026)
        cls.period = env["security.payroll.period"].create({
            "date_from": "2026-05-01",
            "date_to": "2026-05-31",
            "rule_set_id": cls.rule_set.id,
        })

        # Public holiday on 2026-05-01 (Workers Day)
        env["security.public.holiday"].create({
            "name": "Workers Day E2E",
            "country_code": "NA",
            "holiday_date": "2026-05-01",
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_slot(self, shift_date, shift_template=None):
        """Create a roster slot for cls.guard on the given date."""
        template = shift_template or self.day_shift
        return self.env["security.roster.slot"].create({
            "shift_date": shift_date,
            "post_id": self.post.id,
            "shift_template_id": template.id,
            "employee_id": self.guard.id,
        })

    def _make_attendance(self, shift_date, check_in_str, check_out_str, shift_template=None):
        """Create a slot + attendance record with real check-in/out datetimes."""
        slot = self._make_slot(shift_date, shift_template)
        return self.env["security.attendance.record"].create({
            "roster_slot_id": slot.id,
            "check_in": check_in_str,
            "check_out": check_out_str,
        })

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_payslip_generates_from_period(self):
        """Period generates exactly one payslip for the guard."""
        self._make_attendance("2026-05-02", "2026-05-02 06:00:00", "2026-05-02 14:00:00")
        self.period.action_generate_payslips()
        payslips = self.env["security.payslip"].search([
            ("period_id", "=", self.period.id),
            ("employee_id", "=", self.guard.id),
        ])
        self.assertEqual(len(payslips), 1, "Exactly one payslip must be generated per guard.")

    def test_normal_hours_compute_gross_pay(self):
        """8 normal hours at 15 NAD/hr → total_earnings > 0."""
        # 2026-05-04 is a Monday (normal weekday)
        self._make_attendance("2026-05-04", "2026-05-04 06:00:00", "2026-05-04 14:00:00")
        self.period.action_generate_payslips()
        payslip = self.env["security.payslip"].search([
            ("period_id", "=", self.period.id),
            ("employee_id", "=", self.guard.id),
        ], limit=1)
        self.assertTrue(payslip, "Payslip must exist after generate.")
        self.assertGreater(payslip.total_earnings, 0, "Normal-hour attendance must produce earnings.")

    def test_sunday_premium_applied(self):
        """Sunday shift earns 1.5× rate; total_earnings greater than Monday equivalent."""
        # Establish a Monday baseline (2026-05-04)
        slot_mon = self._make_slot("2026-05-04")
        self.env["security.attendance.record"].create({
            "roster_slot_id": slot_mon.id,
            "check_in": "2026-05-04 06:00:00",
            "check_out": "2026-05-04 14:00:00",
        })
        self.period.action_generate_payslips()
        payslip = self.env["security.payslip"].search([
            ("period_id", "=", self.period.id),
            ("employee_id", "=", self.guard.id),
        ], limit=1)
        monday_earnings = payslip.total_earnings

        # Add a Sunday shift (2026-05-03 is a Sunday)
        slot_sun = self._make_slot("2026-05-03")
        self.env["security.attendance.record"].create({
            "roster_slot_id": slot_sun.id,
            "check_in": "2026-05-03 06:00:00",
            "check_out": "2026-05-03 14:00:00",
        })
        payslip.action_compute_from_sources()
        earnings_with_sunday = payslip.total_earnings

        self.assertGreater(
            earnings_with_sunday,
            monday_earnings,
            "Adding a Sunday shift (1.5×) must increase total earnings.",
        )

    def test_public_holiday_premium_applied(self):
        """Public holiday hours earn 1.5×; gross must exceed normal-only equivalent."""
        # 2026-05-01 is registered as a public holiday in setUpClass
        self._make_attendance("2026-05-01", "2026-05-01 06:00:00", "2026-05-01 14:00:00")
        self.period.action_generate_payslips()
        payslip = self.env["security.payslip"].search([
            ("period_id", "=", self.period.id),
            ("employee_id", "=", self.guard.id),
        ], limit=1)
        self.assertTrue(payslip, "Payslip must exist.")
        # 8 normal hours at 15 NAD = 120.  With 1.5× public holiday: 8 * 15 * 1.5 = 180.
        normal_equivalent = 8.0 * self.grade_a.hourly_rate
        self.assertGreater(
            payslip.total_earnings,
            normal_equivalent,
            "Public holiday hours must earn more than normal-rate equivalent.",
        )

    def test_ssc_deduction_computed(self):
        """SSC deduction line with code 'SSC' is created and has a positive amount."""
        # Full-day attendance to generate meaningful earnings
        self._make_attendance("2026-05-06", "2026-05-06 06:00:00", "2026-05-06 14:00:00")
        self.period.action_generate_payslips()
        payslip = self.env["security.payslip"].search([
            ("period_id", "=", self.period.id),
            ("employee_id", "=", self.guard.id),
        ], limit=1)
        self.assertTrue(payslip, "Payslip must exist.")
        ssc_lines = payslip.deduction_line_ids.filtered(lambda l: l.code == "SSC")
        self.assertTrue(len(ssc_lines) > 0, "An SSC deduction line must be created.")
        self.assertGreater(
            sum(ssc_lines.mapped("amount")),
            0,
            "SSC deduction amount must be positive.",
        )

    def test_net_pay_never_negative(self):
        """Net pay must be >= 0 even with all statutory deductions applied."""
        self._make_attendance("2026-05-07", "2026-05-07 06:00:00", "2026-05-07 14:00:00")
        self.period.action_generate_payslips()
        payslip = self.env["security.payslip"].search([
            ("period_id", "=", self.period.id),
            ("employee_id", "=", self.guard.id),
        ], limit=1)
        self.assertTrue(payslip, "Payslip must exist.")
        self.assertGreaterEqual(payslip.net_pay, 0, "Net pay must never be negative.")

    def test_payslip_confirm_and_paid_state_machine(self):
        """Payslip state transitions: draft → confirmed → paid."""
        self._make_attendance("2026-05-08", "2026-05-08 06:00:00", "2026-05-08 14:00:00")
        self.period.action_generate_payslips()
        payslip = self.env["security.payslip"].search([
            ("period_id", "=", self.period.id),
            ("employee_id", "=", self.guard.id),
        ], limit=1)
        self.assertTrue(payslip, "Payslip must exist.")
        self.assertEqual(payslip.state, "draft", "New payslip must start in draft.")
        payslip.action_confirm()
        self.assertEqual(payslip.state, "confirmed", "Payslip must transition to confirmed.")
        payslip.action_mark_paid()
        self.assertEqual(payslip.state, "paid", "Payslip must transition to paid.")
