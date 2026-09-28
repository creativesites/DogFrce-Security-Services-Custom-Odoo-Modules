from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestResponsibility(TransactionCase):
    """Roster -> Responsibility -> Task, and the pipeline readiness."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        group_user = cls.env.ref("base.group_user")
        cls.ops_user = cls.env["res.users"].create({"name": "Ops", "login": "resp-ops@test", "group_ids": [(6, 0, [group_user.id])], "tz": "Africa/Lusaka"})
        cls.admin_user = cls.env["res.users"].create({"name": "Admin", "login": "resp-admin@test", "group_ids": [(6, 0, [group_user.id])], "tz": "Africa/Lusaka"})
        cls.gm_user = cls.env["res.users"].create({
            "name": "GM", "login": "resp-gm@test", "tz": "Africa/Lusaka",
            "group_ids": [(6, 0, [group_user.id, cls.env.ref("security_base.group_security_manager").id])],
        })
        cls.ops = cls.env["hr.employee"].create({"name": "Ops Supervisor", "user_id": cls.ops_user.id, "tz": "Africa/Lusaka"})
        cls.admin = cls.env["hr.employee"].create({"name": "Admin Clerk", "user_id": cls.admin_user.id, "tz": "Africa/Lusaka"})
        cls.guard = cls.env["hr.employee"].create({"name": "Guard One", "security_guard": True})

        partner = cls.env["res.partner"].create({"name": "ABC Mall", "is_company": True})
        cls.site_a = cls.env["security.client.site"].create({"name": "ABC Mall", "partner_id": partner.id})
        cls.site_b = cls.env["security.client.site"].create({"name": "Quiet Depot", "partner_id": partner.id})
        post_type = cls.env["security.post.type"].create({"name": "Standard"})
        cls.post_a = cls.env["security.post"].create({"name": "Main Gate", "site_id": cls.site_a.id, "post_type_id": post_type.id})
        cls.shift = cls.env["security.shift.template"].create({"name": "Day", "start_hour": 6.0, "end_hour": 18.0})

        cls.template = cls.env["security.work.checklist.template"].create({"name": "Attendance", "code": "test.attendance"})
        cls.register = cls.env["security.work.responsibility"].create({
            "name": "Register attendance", "sequence": 10, "employee_id": cls.ops.id,
            "checklist_template_id": cls.template.id, "due_hour": 10.0,
            "why_it_matters": "Payroll is calculated from it.",
        })
        cls.confirm = cls.env["security.work.responsibility"].create({
            "name": "Confirm attendance", "sequence": 20, "employee_id": cls.admin.id,
            "checklist_template_id": cls.template.id, "due_hour": 12.0, "depends_on_id": cls.register.id,
        })

    def _roster(self, day, site_post=None, employee=None, state="confirmed"):
        return self.env["security.roster.slot"].create({
            "shift_date": day, "post_id": (site_post or self.post_a).id,
            "shift_template_id": self.shift.id, "employee_id": (employee or self.guard).id, "state": state,
        })

    def test_tasks_only_for_rostered_site_days(self):
        today = fields.Date.context_today(self.register)
        self._roster(today)
        created = self.register._materialize(horizon_days=3)
        self.assertEqual(len(created), 1, "one rostered site-day -> one task; the unrostered site gets none")
        task = created
        self.assertEqual(task.site_id, self.site_a)
        self.assertEqual(task.roster_date, today)
        self.assertEqual(task.employee_id, self.ops)
        self.assertIn("ABC Mall", task.name)

    def test_materialize_is_idempotent(self):
        today = fields.Date.context_today(self.register)
        self._roster(today)
        self.register._materialize(horizon_days=2)
        self.assertFalse(self.register._materialize(horizon_days=2))

    def test_unassigned_or_cancelled_slots_create_nothing(self):
        today = fields.Date.context_today(self.register)
        self._roster(today, state="cancelled")
        self.assertFalse(self.register._materialize(horizon_days=1))

    def test_roster_change_withdraws_untouched_future_tasks(self):
        tomorrow = fields.Date.context_today(self.register) + timedelta(days=1)
        slot = self._roster(tomorrow)
        task = self.register._materialize(horizon_days=3)
        slot.state = "cancelled"
        self.register._materialize(horizon_days=3)
        self.assertEqual(task.state, "cancelled")

    def test_due_time_is_local(self):
        today = fields.Date.context_today(self.register)
        self._roster(today)
        task = self.register._materialize(horizon_days=1)
        # 10:00 in Lusaka (UTC+2) is 08:00 UTC.
        self.assertEqual(task.due_at.hour, 8)

    def test_downstream_step_waits_for_upstream(self):
        today = fields.Date.context_today(self.register)
        self._roster(today)
        reg = self.register._materialize(horizon_days=1)
        conf = self.confirm._materialize(horizon_days=1)
        self.assertEqual(conf.readiness, "waiting")
        self.assertIn("Register attendance", conf.waiting_on)
        reg.action_submit()
        conf.invalidate_recordset(["readiness", "waiting_on"])
        self.assertEqual(conf.readiness, "ready")

    def test_my_today_is_the_employees_own_work_with_why(self):
        today = fields.Date.context_today(self.register)
        self._roster(today)
        self.register._materialize(horizon_days=1)
        self.confirm._materialize(horizon_days=1)
        mine = self.env["security.work.task"].with_user(self.ops_user).get_my_today()
        self.assertEqual([t["responsibility"] for t in mine["tasks"]], ["Register attendance"])
        self.assertEqual(mine["tasks"][0]["why_it_matters"], "Payroll is calculated from it.")
        theirs = self.env["security.work.task"].with_user(self.admin_user).get_my_today()
        self.assertEqual(theirs["tasks"][0]["readiness"], "waiting")

    def test_team_today_shows_the_pipeline_per_site_to_managers_only(self):
        today = fields.Date.context_today(self.register)
        self._roster(today)
        self.register._materialize(horizon_days=1)
        self.confirm._materialize(horizon_days=1)
        with self.assertRaises(AccessError):
            self.env["security.work.task"].with_user(self.ops_user).get_team_today()
        team = self.env["security.work.task"].with_user(self.gm_user).get_team_today()
        self.assertEqual([s["name"] for s in team["steps"]], ["Register attendance", "Confirm attendance"])
        row = team["pipeline"][0]
        self.assertEqual(row["site"], "ABC Mall")
        self.assertEqual(row["cells"][self.confirm.id]["readiness"], "waiting")
        self.assertEqual(sum(len(p["expected"]) for p in team["people"]), 2)

    def test_viewer_context_comes_from_groups(self):
        Task = self.env["security.work.task"]
        self.assertEqual(Task.with_user(self.ops_user).get_viewer_context(),
                         {"is_supervisor": False, "is_manager": False, "is_owner": False})
        gm = Task.with_user(self.gm_user).get_viewer_context()
        self.assertTrue(gm["is_manager"] and gm["is_supervisor"])
