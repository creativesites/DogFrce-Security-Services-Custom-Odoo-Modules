"""
Unit-level integration tests for payslip anomaly detection.

Each test constructs a minimal payslip with specific attendance patterns
and verifies the resulting anomaly_flags and anomaly_score.

Coverage:
  - Clean record → no flags
  - AWOL threshold (2 triggers, 1 does not)
  - High unpaid-hours ratio (> 35 %) triggers flag
  - Missing checkout flag (>= 2 records)
"""

from odoo.tests.common import TransactionCase


class TestAnomalyDetection(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Rule set
        cls.rule_set = cls.env["security.payroll.rule.set"].search(
            [("country_code", "=", "NA")], limit=1
        )
        if not cls.rule_set:
            cls.rule_set = cls.env["security.payroll.rule.set"].create({
                "name": "Anomaly Test NA Rule Set",
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

        # Shared infrastructure
        cls.partner = cls.env["res.partner"].create({"name": "Anomaly Test Client"})
        cls.site = cls.env["security.client.site"].create({
            "name": "Anomaly Site",
            "partner_id": cls.partner.id,
        })
        cls.post_type = cls.env["security.post.type"].create({"name": "Anomaly Post Type"})
        cls.post = cls.env["security.post"].create({
            "name": "Anomaly Post",
            "partner_id": cls.partner.id,
            "site_id": cls.site.id,
            "post_type_id": cls.post_type.id,
        })
        cls.shift_template = cls.env["security.shift.template"].create({
            "name": "8h Anomaly Shift",
            "start_hour": 6.0,
            "end_hour": 14.0,
        })

        cls.guard = cls.env["hr.employee"].create({
            "name": "Anomaly Test Guard",
            "security_guard": True,
            "security_hourly_rate": 20.0,
        })

        cls.period = cls.env["security.payroll.period"].create({
            "date_from": "2026-06-01",
            "date_to": "2026-06-30",
            "rule_set_id": cls.rule_set.id,
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_slot(self, date_str):
        return self.env["security.roster.slot"].create({
            "shift_date": date_str,
            "post_id": self.post.id,
            "shift_template_id": self.shift_template.id,
            "employee_id": self.guard.id,
        })

    def _payslip_with_records(self, attendance_ids):
        """Create a fresh payslip for the guard and link the given attendance records."""
        payslip = self.env["security.payslip"].create({
            "period_id": self.period.id,
            "employee_id": self.guard.id,
        })
        payslip.attendance_record_ids = [(6, 0, attendance_ids)]
        payslip.action_compute_from_sources()
        return payslip

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_no_anomaly_clean_record(self):
        """All-present guard with no AWOL, no late, no missing checkout → no anomaly flags."""
        records = []
        for day in ("2026-06-02", "2026-06-03", "2026-06-04"):
            slot = self._make_slot(day)
            rec = self.env["security.attendance.record"].create({
                "roster_slot_id": slot.id,
                "check_in": day + " 06:00:00",
                "check_out": day + " 14:00:00",
            })
            records.append(rec.id)

        payslip = self._payslip_with_records(records)
        self.assertFalse(
            payslip.anomaly_flags,
            "No anomaly flags expected for a clean attendance record.",
        )
        self.assertEqual(payslip.anomaly_score, 0)

    def test_awol_threshold(self):
        """Exactly 2 AWOL records triggers the flag; 1 AWOL alone does not."""
        # One AWOL → no flag
        slot_a = self._make_slot("2026-06-09")
        rec_1 = self.env["security.attendance.record"].create({
            "roster_slot_id": slot_a.id,
            "manual_presence": "awol",
            "absence_type": "awol",
        })
        payslip_one = self._payslip_with_records([rec_1.id])
        self.assertFalse(
            payslip_one.anomaly_flags,
            "A single AWOL should NOT trigger an anomaly flag.",
        )

        # Two AWOL → flag
        slot_b = self._make_slot("2026-06-10")
        rec_2 = self.env["security.attendance.record"].create({
            "roster_slot_id": slot_b.id,
            "manual_presence": "awol",
            "absence_type": "awol",
        })
        payslip_two = self._payslip_with_records([rec_1.id, rec_2.id])
        self.assertTrue(
            payslip_two.anomaly_flags,
            "Two AWOL records MUST trigger an anomaly flag.",
        )
        self.assertIn("AWOL", payslip_two.anomaly_flags)
        self.assertGreater(payslip_two.anomaly_score, 0)

    def test_high_unpaid_ratio(self):
        """
        Guard works only 1 of 3 scheduled hours per shift (unpaid_hours/total > 35 %)
        → high no-work-no-pay ratio flag is raised.
        """
        # Schedule 6:00–14:00 (8 h), guard arrives at 13:00 (only 1 h valid)
        records = []
        for day in ("2026-06-16", "2026-06-17"):
            slot = self._make_slot(day)
            rec = self.env["security.attendance.record"].create({
                "roster_slot_id": slot.id,
                "check_in": day + " 13:00:00",
                "check_out": day + " 14:00:00",
            })
            records.append(rec.id)

        payslip = self._payslip_with_records(records)
        # Each shift: 8 scheduled, 1 valid → unpaid = 7 h out of 8 total = 87.5 %
        # Should exceed the 35 % threshold
        self.assertTrue(
            payslip.anomaly_flags,
            "High unpaid-hours ratio (> 35 %%) must set an anomaly flag.",
        )
        self.assertIn("no-work-no-pay", payslip.anomaly_flags)

    def test_missing_checkout_flag(self):
        """Two or more records with check_in but no check_out trigger the missing-checkout flag."""
        records = []
        for day in ("2026-06-23", "2026-06-24"):
            slot = self._make_slot(day)
            rec = self.env["security.attendance.record"].create({
                "roster_slot_id": slot.id,
                "check_in": day + " 06:00:00",
                # no check_out
            })
            records.append(rec.id)

        payslip = self._payslip_with_records(records)
        self.assertTrue(
            payslip.anomaly_flags,
            "Two missing check-outs must trigger an anomaly flag.",
        )
        self.assertIn("Missing check-out", payslip.anomaly_flags)
