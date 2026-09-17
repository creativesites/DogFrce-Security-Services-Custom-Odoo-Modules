from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestExpectedWorkItemMaterialization(TransactionCase):
    """docs/deployguard/09-adoption-engine.md §2. Materialisation always
    looks at the day/week that has just closed (T-1), so every fixture
    below is dated yesterday (or the week before), never today."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Item = cls.env["security.adoption.expected.work.item"]
        cls.def_attendance = cls.env.ref("security_adoption.def_attendance_post")
        cls.def_site_visit = cls.env.ref("security_adoption.def_site_visit")
        cls.def_training = cls.env.ref("security_adoption.def_training_mandatory")

        cls.supervisor = cls.env["hr.employee"].create({"name": "Materialize Supervisor", "security_guard": True})
        cls.partner = cls.env["res.partner"].create({"name": "Materialize Client", "is_company": True})
        cls.site = cls.env["security.client.site"].create({
            "name": "Materialize Site", "partner_id": cls.partner.id, "supervisor_id": cls.supervisor.id,
        })
        cls.post_type = cls.env["security.post.type"].create({"name": "Standard"})
        cls.post = cls.env["security.post"].create({
            "name": "Gate", "site_id": cls.site.id, "post_type_id": cls.post_type.id,
        })
        cls.shift_template = cls.env["security.shift.template"].create({"name": "Day"})

    def _roster_slot(self, shift_date, employee=None, state="assigned"):
        return self.env["security.roster.slot"].create({
            "post_id": self.post.id, "shift_date": shift_date,
            "shift_template_id": self.shift_template.id,
            "employee_id": (employee or self.supervisor).id, "state": state,
        })

    def test_attendance_post_fulfilled_when_batch_reviewed(self):
        yesterday = fields.Date.context_today(self.env["security.adoption.expected.work.item"]) - timedelta(days=1)
        self._roster_slot(yesterday)
        batch = self.env["security.attendance.batch"].create({
            "attendance_date": yesterday, "site_id": self.site.id, "state": "reviewed",
        })
        self.Item.action_materialize_all()
        item = self.Item.search([
            ("definition_id", "=", self.def_attendance.id), ("employee_id", "=", self.supervisor.id),
            ("period_date", "=", yesterday),
        ])
        self.assertEqual(len(item), 1)
        self.assertEqual(item.state, "fulfilled")
        self.assertEqual(item.source_model, "security.attendance.batch")
        self.assertEqual(item.source_res_id, batch.id)

    def test_attendance_post_missed_when_no_batch(self):
        yesterday = fields.Date.context_today(self.Item) - timedelta(days=1)
        self._roster_slot(yesterday)
        self.Item.action_materialize_all()
        item = self.Item.search([
            ("definition_id", "=", self.def_attendance.id), ("employee_id", "=", self.supervisor.id),
            ("period_date", "=", yesterday),
        ])
        self.assertEqual(item.state, "missed")

    def test_attendance_post_excused_no_shift(self):
        yesterday = fields.Date.context_today(self.Item) - timedelta(days=1)
        # No roster slot created for this date -> no_shift excusal.
        self.Item.action_materialize_all()
        item = self.Item.search([
            ("definition_id", "=", self.def_attendance.id), ("employee_id", "=", self.supervisor.id),
            ("period_date", "=", yesterday),
        ])
        self.assertEqual(item.state, "excused")
        self.assertEqual(item.excusal_reason, "no_shift")

    def test_attendance_post_excused_on_approved_leave(self):
        yesterday = fields.Date.context_today(self.Item) - timedelta(days=1)
        self._roster_slot(yesterday)
        leave_type = self.env["security.leave.type"].create({"name": "Annual", "negative_balance_limit": 30.0})
        leave = self.env["security.leave.request"].create({
            "employee_id": self.supervisor.id, "leave_type_id": leave_type.id,
            "date_from": yesterday, "date_to": yesterday,
        })
        leave.action_approve()
        self.Item.action_materialize_all()
        item = self.Item.search([
            ("definition_id", "=", self.def_attendance.id), ("employee_id", "=", self.supervisor.id),
            ("period_date", "=", yesterday),
        ])
        self.assertEqual(item.state, "excused")
        self.assertEqual(item.excusal_reason, "leave")

    def test_materialize_is_idempotent(self):
        yesterday = fields.Date.context_today(self.Item) - timedelta(days=1)
        self._roster_slot(yesterday)
        self.Item.action_materialize_all()
        count_after_first = self.Item.search_count([("definition_id", "=", self.def_attendance.id)])
        self.Item.action_materialize_all()
        count_after_second = self.Item.search_count([("definition_id", "=", self.def_attendance.id)])
        self.assertEqual(count_after_first, count_after_second)

    def test_site_visit_fulfilled_by_verified_task(self):
        template = self.env.ref("security_work.template_site_visit")
        monday = fields.Date.context_today(self.Item)
        monday -= timedelta(days=monday.weekday())
        if fields.Date.context_today(self.Item).weekday() != 0:
            self.skipTest("site.visit only materializes on Mondays -- not exercising the date-gate here.")
        last_week_start = monday - timedelta(days=7)
        task = self.env["security.work.task"].create({
            "name": "Weekly visit", "employee_id": self.supervisor.id, "site_id": self.site.id,
            "checklist_template_id": template.id,
            "due_at": fields.Datetime.to_string(last_week_start + timedelta(days=3, hours=17)),
        })
        task.action_start()
        task.action_submit()
        self.Item.action_materialize_all()
        item = self.Item.search([
            ("definition_id", "=", self.def_site_visit.id), ("employee_id", "=", self.supervisor.id),
            ("period_date", "=", last_week_start),
        ])
        self.assertEqual(item.state, "fulfilled")

    def test_training_mandatory_fulfilled_on_completion(self):
        author = self.env["res.users"].create({
            "name": "Materialize Training Author", "login": "materialize-training@access-control.test",
            "group_ids": [(6, 0, [self.env.ref("security_training.group_training_supervisor").id])],
        })
        env = self.env.with_user(author)
        course = env["security.training.course"].create({"name": "Materialize Course"})
        version = course.version_ids
        env["security.training.section"].create({"course_version_id": version.id, "name": "S1"})
        version.action_submit_for_review()
        version.with_user(self.env.ref("base.user_admin")).action_approve()

        due_date = fields.Date.context_today(self.Item) - timedelta(days=1)
        assignment = self.env["security.training.assignment"].create({
            "employee_id": self.supervisor.id, "course_id": course.id, "due_date": due_date,
        })
        assignment.write({"state": "completed", "completed_at": fields.Datetime.to_string(
            fields.Datetime.to_datetime(due_date) - timedelta(hours=1)
        )})

        self.Item.action_materialize_all()
        item = self.Item.search([
            ("definition_id", "=", self.def_training.id),
            ("source_model", "=", "security.training.assignment"), ("source_res_id", "=", assignment.id),
        ])
        self.assertEqual(item.state, "fulfilled")
        self.assertTrue(item.on_time)
