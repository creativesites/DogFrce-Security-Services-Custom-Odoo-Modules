from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAutoCompletion(TransactionCase):
    """docs/deployguard/BUILD-STATUS-AND-PHASE-PLAN.md Phase 3.2. Exercises
    the mechanism directly via _handle_bus_event rather than requiring
    security_attendance to be installed alongside security_work."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Autocomplete Test Client"})
        cls.site = cls.env["security.client.site"].create({
            "name": "Autocomplete Test Site", "partner_id": cls.partner.id,
        })
        cls.template = cls.env["security.work.checklist.template"].search(
            [("code", "=", "attendance.post")], limit=1
        )
        cls.employee = cls.env["hr.employee"].create({"name": "Autocomplete Test Guard"})

    def _task(self, **overrides):
        vals = {
            "name": "Post attendance",
            "employee_id": self.employee.id,
            "site_id": self.site.id,
            "checklist_template_id": self.template.id,
            "due_at": "2026-08-15 17:00:00",
            "state": "open",
        }
        vals.update(overrides)
        return self.env["security.work.task"].create(vals)

    def _dispatch(self, event_name="attendance.batch.reviewed", **payload_overrides):
        payload = {"site_id": self.site.id, "attendance_date": "2026-08-15"}
        payload.update(payload_overrides)
        self.env["security.work.task"]._handle_bus_event(
            event_name, "security.attendance.batch", 999, payload
        )

    def test_matching_open_task_is_auto_verified(self):
        task = self._task()
        self._dispatch()
        self.assertEqual(task.state, "verified")
        self.assertTrue(task.verified_at)

    def test_submitted_task_is_also_auto_verified(self):
        task = self._task(state="submitted")
        self._dispatch()
        self.assertEqual(task.state, "verified")

    def test_already_verified_task_is_left_alone(self):
        task = self._task(state="verified")
        original_verified_at = task.verified_at
        self._dispatch()
        self.assertEqual(task.verified_at, original_verified_at)

    def test_cancelled_task_is_not_reopened(self):
        task = self._task(state="cancelled")
        self._dispatch()
        self.assertEqual(task.state, "cancelled")

    def test_wrong_site_does_not_match(self):
        other_partner = self.env["res.partner"].create({"name": "Other Client"})
        other_site = self.env["security.client.site"].create({
            "name": "Other Site", "partner_id": other_partner.id,
        })
        task = self._task(site_id=other_site.id)
        self._dispatch()
        self.assertEqual(task.state, "open")

    def test_wrong_date_does_not_match(self):
        task = self._task(due_at="2026-08-16 17:00:00")
        self._dispatch()
        self.assertEqual(task.state, "open")

    def test_wrong_template_does_not_match(self):
        other_template = self.env["security.work.checklist.template"].create({
            "name": "Not Attendance", "code": "not.attendance",
        })
        task = self._task(checklist_template_id=other_template.id)
        self._dispatch()
        self.assertEqual(task.state, "open")

    def test_matched_fact_is_recorded_as_a_chatter_note(self):
        task = self._task()
        self._dispatch()
        bodies = " ".join(task.message_ids.mapped("body"))
        self.assertIn("999", bodies)

    def test_missing_payload_fields_are_a_safe_no_op(self):
        task = self._task()
        self._dispatch(site_id=False, attendance_date=False)
        self.assertEqual(task.state, "open")

    def test_dispatch_via_the_real_bus_reaches_the_task(self):
        """End-to-end through security.event.log, not just the direct call."""
        task = self._task()
        self.env["security.event.log"].register_event(
            "attendance.batch.reviewed", "security.attendance.batch", 42,
            {"site_id": self.site.id, "attendance_date": "2026-08-15"},
        )
        self.assertEqual(task.state, "verified")
