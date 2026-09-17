from odoo.tests.common import TransactionCase


class TestHoursEquityAudit(TransactionCase):
    """docs/ROSTERING_SIMPLIFICATION_PLAN.md §3/A7b."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.tz = "UTC"
        cls.env.company.partner_id.tz = "UTC"
        cls.partner = cls.env["res.partner"].create({"name": "Hours Audit Client"})
        cls.site = cls.env["security.client.site"].create({
            "name": "Hours Audit Site", "partner_id": cls.partner.id,
        })
        cls.post_type = cls.env["security.post.type"].create({"name": "Hours Audit Post Type"})
        cls.post = cls.env["security.post"].create({
            "name": "Hours Audit Post", "partner_id": cls.partner.id,
            "site_id": cls.site.id, "post_type_id": cls.post_type.id,
        })
        cls.template = cls.env["security.shift.template"].create({
            "name": "Hours Audit Shift", "start_hour": 6.0, "end_hour": 14.0,
        })

    def _record_for(self, employee, date_str, worked_hours=8.0):
        """Create a shift template scheduled for exactly `worked_hours`, and
        check the guard in/out for the whole window.

        payable_hours = valid_hours (the overlap between the scheduled shift
        and the actual check-in/out) + approved overtime. valid_hours can
        never exceed the *scheduled* window, so to get a guard's payable
        hours above or below the team average this has to vary the shift
        length, not just how long they happened to stay checked in against a
        fixed shift.
        """
        template = self.env["security.shift.template"].create({
            "name": f"Audit shift {worked_hours}h",
            "start_hour": 6.0,
            "end_hour": 6.0 + worked_hours,
        })
        slot = self.env["security.roster.slot"].create({
            "shift_date": date_str, "post_id": self.post.id,
            "shift_template_id": template.id, "employee_id": employee.id,
        })
        record = self.env["security.attendance.record"].create({"roster_slot_id": slot.id})
        record.write({
            "check_in": f"{date_str} 06:00:00",
            "check_out": f"{date_str} {6 + worked_hours:02.0f}:00:00",
        })
        return record

    def test_no_data_yields_empty_result(self):
        audit = self.env["security.attendance.hours.audit"].create({
            "date_from": "2035-08-01", "date_to": "2035-08-31",
        })
        audit.action_run()
        self.assertFalse(audit.line_ids)
        self.assertEqual(audit.average_payable_hours, 0.0)

    def test_outliers_flagged_both_directions(self):
        guard_normal = self.env["hr.employee"].create({"name": "Normal Guard"})
        guard_over = self.env["hr.employee"].create({"name": "Over-rostered Guard"})
        guard_under = self.env["hr.employee"].create({"name": "Under-rostered Guard"})

        # Team average ~= 8h; over-rostered guard well above +20%, under well below -20%.
        self._record_for(guard_normal, "2035-08-03", worked_hours=8.0)
        self._record_for(guard_over, "2035-08-03", worked_hours=12.0)
        self._record_for(guard_under, "2035-08-03", worked_hours=2.0)

        audit = self.env["security.attendance.hours.audit"].create({
            "date_from": "2035-08-01", "date_to": "2035-08-31",
        })
        audit.action_run()

        lines_by_employee = {line.employee_id: line for line in audit.line_ids}
        self.assertEqual(lines_by_employee[guard_over].flag, "over")
        self.assertEqual(lines_by_employee[guard_under].flag, "under")
        self.assertEqual(audit.over_count, 1)
        self.assertEqual(audit.under_count, 1)

    def test_within_band_is_not_flagged(self):
        guard_a = self.env["hr.employee"].create({"name": "Guard A"})
        guard_b = self.env["hr.employee"].create({"name": "Guard B"})
        self._record_for(guard_a, "2035-08-03", worked_hours=8.0)
        self._record_for(guard_b, "2035-08-03", worked_hours=8.5)

        audit = self.env["security.attendance.hours.audit"].create({
            "date_from": "2035-08-01", "date_to": "2035-08-31",
        })
        audit.action_run()
        self.assertTrue(all(line.flag == "normal" for line in audit.line_ids))

    def test_site_filter_scopes_the_audit(self):
        other_site = self.env["security.client.site"].create({
            "name": "Other Site", "partner_id": self.partner.id,
        })
        other_post = self.env["security.post"].create({
            "name": "Other Post", "partner_id": self.partner.id,
            "site_id": other_site.id, "post_type_id": self.post_type.id,
        })
        guard = self.env["hr.employee"].create({"name": "Cross-Site Guard"})
        self._record_for(guard, "2035-08-03", worked_hours=8.0)

        other_slot = self.env["security.roster.slot"].create({
            "shift_date": "2035-08-04", "post_id": other_post.id,
            "shift_template_id": self.template.id, "employee_id": guard.id,
        })
        other_record = self.env["security.attendance.record"].create({
            "roster_slot_id": other_slot.id,
        })
        other_record.write({"check_in": "2035-08-04 06:00:00", "check_out": "2035-08-04 18:00:00"})

        audit = self.env["security.attendance.hours.audit"].create({
            "date_from": "2035-08-01", "date_to": "2035-08-31",
            "site_id": self.site.id,
        })
        audit.action_run()
        self.assertEqual(len(audit.line_ids), 1)
        self.assertAlmostEqual(audit.line_ids.payable_hours, 8.0, places=1)

    def test_rerun_clears_previous_lines(self):
        guard = self.env["hr.employee"].create({"name": "Rerun Guard"})
        self._record_for(guard, "2035-08-03", worked_hours=8.0)
        audit = self.env["security.attendance.hours.audit"].create({
            "date_from": "2035-08-01", "date_to": "2035-08-31",
        })
        audit.action_run()
        audit.action_run()
        self.assertEqual(len(audit.line_ids), 1, "re-running must not duplicate lines")
