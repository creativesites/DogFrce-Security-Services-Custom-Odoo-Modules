from datetime import timedelta

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestScheduleRule(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create({"name": "Recurrence Test Guard"})
        cls.template = cls.env["security.work.checklist.template"].create({
            "name": "Recurrence Test Checklist", "code": "recurrence.test",
        })

    def _rule(self, **overrides):
        vals = {
            "name": "Daily test rule",
            "checklist_template_id": self.template.id,
            "employee_id": self.employee.id,
            "monday": True, "tuesday": True, "wednesday": True,
            "thursday": True, "friday": True, "saturday": True, "sunday": True,
        }
        vals.update(overrides)
        return self.env["security.work.schedule.rule"].create(vals)

    def test_materialize_creates_one_task_per_day_in_horizon(self):
        rule = self._rule()
        created = rule._materialize(horizon_days=7)
        self.assertEqual(len(created), 7)

    def test_materialize_is_idempotent(self):
        rule = self._rule()
        rule._materialize(horizon_days=7)
        second_run = rule._materialize(horizon_days=7)
        self.assertEqual(len(second_run), 0, "re-running must not duplicate tasks")

    def test_weekday_restriction_is_respected(self):
        rule = self._rule(
            monday=True, tuesday=False, wednesday=False,
            thursday=False, friday=False, saturday=False, sunday=False,
        )
        created = rule._materialize(horizon_days=7)
        for task in created:
            self.assertEqual(task.due_at.weekday(), 0, "only Mondays should be created")

    def test_due_hour_is_applied(self):
        rule = self._rule(due_hour=9.5)
        created = rule._materialize(horizon_days=1)
        self.assertEqual(created[0].due_at.hour, 9)
        self.assertEqual(created[0].due_at.minute, 30)

    def test_last_materialized_date_is_stamped(self):
        rule = self._rule()
        self.assertFalse(rule.last_materialized_date)
        rule._materialize(horizon_days=1)
        self.assertTrue(rule.last_materialized_date)

    def test_inactive_rule_is_skipped_by_action_materialize_all(self):
        rule = self._rule(active=False)
        Task = self.env["security.work.task"]
        before = Task.search_count([("checklist_template_id", "=", self.template.id)])
        self.env["security.work.schedule.rule"].action_materialize_all()
        after = Task.search_count([("checklist_template_id", "=", self.template.id)])
        self.assertEqual(before, after)

    def test_site_is_carried_onto_generated_tasks(self):
        partner = self.env["res.partner"].create({"name": "Recurrence Test Client"})
        site = self.env["security.client.site"].create({
            "name": "Recurrence Test Site", "partner_id": partner.id,
        })
        rule = self._rule(site_id=site.id)
        created = rule._materialize(horizon_days=1)
        self.assertEqual(created.site_id, site)
