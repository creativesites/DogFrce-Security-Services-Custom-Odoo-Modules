"""
Integration tests for the end-to-end payroll pipeline.

Coverage:
  - Payslip generation for security guards
  - AWOL anomaly flag (threshold >= 2)
  - Late arrival anomaly flag (threshold >= 3)
  - Net pay is non-negative for confirmed payslips
  - Period state machine: draft → processed → closed
"""

from odoo.tests.common import TransactionCase


class TestPayrollPipeline(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ------------------------------------------------------------------ #
        # Rule set (Namibia)
        # ------------------------------------------------------------------ #
        cls.rule_set = cls.env["security.payroll.rule.set"].search(
            [("country_code", "=", "NA")], limit=1
        )
        if not cls.rule_set:
            cls.rule_set = cls.env["security.payroll.rule.set"].create({
                "name": "Test NA Rule Set",
                "country_code": "NA",
                "currency_id": cls.env.ref("base.NAD").id,
                "effective_from": "2026-01-01",
                "employee_ssc_rate": 0.009,
                "employer_ssc_rate": 0.009,
                "ssc_salary_cap": 9000.0,
                "sunday_multiplier": 1.5,
                "public_holiday_multiplier": 1.5,
                "saturday_multiplier": 1.25,
                "night_shift_multiplier": 1.15,
                "overtime_multiplier": 1.5,
            })
            cls.env["security.tax.bracket"].create({
                "rule_set_id": cls.rule_set.id,
                "lower_bound": 0.0,
                "upper_bound": 100000.0,
                "fixed_amount": 0.0,
                "rate": 0.00,
            })

        # ------------------------------------------------------------------ #
        # Client / Site / Post infrastructure
        # ------------------------------------------------------------------ #
        cls.partner = cls.env["res.partner"].create({"name": "Test Client Pipeline"})
        cls.site = cls.env["security.client.site"].create({
            "name": "Pipeline Test Site",
            "partner_id": cls.partner.id,
        })
        cls.post_type = cls.env["security.post.type"].create({"name": "Pipeline Post Type"})
        cls.post = cls.env["security.post"].create({
            "name": "Pipeline Post",
            "partner_id": cls.partner.id,
            "site_id": cls.site.id,
            "post_type_id": cls.post_type.id,
        })
        cls.shift_template = cls.env["security.shift.template"].create({
            "name": "08h Day Shift",
            "start_hour": 6.0,
            "end_hour": 14.0,
        })

        # ------------------------------------------------------------------ #
        # Guards
        # ------------------------------------------------------------------ #
        cls.guard = cls.env["hr.employee"].create({
            "name": "Pipeline Guard Alpha",
            "security_guard": True,
            "security_hourly_rate": 15.0,
        })
        cls.guard_awol = cls.env["hr.employee"].create({
            "name": "Pipeline Guard AWOL",
            "security_guard": True,
            "security_hourly_rate": 15.0,
        })
        cls.guard_late = cls.env["hr.employee"].create({
            "name": "Pipeline Guard Late",
            "security_guard": True,
            "security_hourly_rate": 15.0,
        })

        # ------------------------------------------------------------------ #
        # Payroll period (May 2026)
        # ------------------------------------------------------------------ #
        cls.period = cls.env["security.payroll.period"].create({
            "date_from": "2026-05-01",
            "date_to": "2026-05-31",
            "rule_set_id": cls.rule_set.id,
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_slot(self, employee, shift_date):
        return self.env["security.roster.slot"].create({
            "shift_date": shift_date,
            "post_id": self.post.id,
            "shift_template_id": self.shift_template.id,
            "employee_id": employee.id,
        })

    def _make_attendance(self, slot, check_in, check_out):
        return self.env["security.attendance.record"].create({
            "roster_slot_id": slot.id,
            "check_in": check_in,
            "check_out": check_out,
        })

    def _make_awol(self, employee, shift_date):
        slot = self._make_slot(employee, shift_date)
        return self.env["security.attendance.record"].create({
            "roster_slot_id": slot.id,
            "manual_presence": "awol",
            "absence_type": "awol",
        })

    def _make_late(self, employee, shift_date):
        """Guard arrives 30 min late — scheduled start is 06:00."""
        slot = self._make_slot(employee, shift_date)
        return self._make_attendance(
            slot,
            check_in=shift_date + " 06:30:00",
            check_out=shift_date + " 14:00:00",
        )

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_payslip_generates_for_guard(self):
        """action_generate_payslips creates exactly one payslip per guard."""
        slot = self._make_slot(self.guard, "2026-05-02")
        self._make_attendance(slot, "2026-05-02 06:00:00", "2026-05-02 14:00:00")

        self.period.action_generate_payslips()

        payslip = self.env["security.payslip"].search([
            ("period_id", "=", self.period.id),
            ("employee_id", "=", self.guard.id),
        ])
        self.assertEqual(len(payslip), 1, "Exactly one payslip should be created per guard.")

    def test_anomaly_flag_awol(self):
        """Two or more AWOL records on a payslip trigger the AWOL anomaly flag."""
        for day in ("2026-05-05", "2026-05-06"):
            self._make_awol(self.guard_awol, day)

        self.period.action_generate_payslips()

        payslip = self.env["security.payslip"].search([
            ("period_id", "=", self.period.id),
            ("employee_id", "=", self.guard_awol.id),
        ], limit=1)
        self.assertTrue(payslip, "Payslip must be generated for AWOL guard.")
        self.assertGreaterEqual(payslip.awol_occurrences, 2)
        self.assertTrue(payslip.anomaly_flags, "AWOL anomaly flag must be set.")
        self.assertIn("AWOL", payslip.anomaly_flags)

    def test_anomaly_flag_late(self):
        """Three or more late arrivals on a payslip trigger the late anomaly flag."""
        for day in ("2026-05-07", "2026-05-08", "2026-05-09"):
            self._make_late(self.guard_late, day)

        self.period.action_generate_payslips()

        payslip = self.env["security.payslip"].search([
            ("period_id", "=", self.period.id),
            ("employee_id", "=", self.guard_late.id),
        ], limit=1)
        self.assertTrue(payslip, "Payslip must be generated for late guard.")
        self.assertGreaterEqual(payslip.late_occurrences, 3)
        self.assertTrue(payslip.anomaly_flags, "Late anomaly flag must be set.")
        self.assertIn("Late arrivals", payslip.anomaly_flags)

    def test_net_pay_positive(self):
        """Confirmed payslip has net_pay >= 0 (normal hours, no deductions exceed earnings)."""
        slot = self._make_slot(self.guard, "2026-05-12")
        self._make_attendance(slot, "2026-05-12 06:00:00", "2026-05-12 14:00:00")

        self.period.action_generate_payslips()

        payslip = self.env["security.payslip"].search([
            ("period_id", "=", self.period.id),
            ("employee_id", "=", self.guard.id),
        ], limit=1)
        payslip.action_confirm()
        self.assertEqual(payslip.state, "confirmed")
        self.assertGreaterEqual(payslip.net_pay, 0.0, "Net pay must not be negative.")

    def test_period_state_machine(self):
        """Period transitions: draft → processed (via generate) → closed."""
        slot = self._make_slot(self.guard, "2026-05-14")
        self._make_attendance(slot, "2026-05-14 06:00:00", "2026-05-14 14:00:00")

        self.assertEqual(self.period.state, "draft")

        self.period.action_generate_payslips()
        self.assertEqual(self.period.state, "processed")

        self.period.action_close()
        self.assertEqual(self.period.state, "closed")

        self.period.action_reset_to_draft()
        self.assertEqual(self.period.state, "draft")
