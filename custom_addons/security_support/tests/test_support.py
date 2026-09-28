import json

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSupport(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        group_user = cls.env.ref("base.group_user")
        cls.staff = cls.env["res.users"].create({
            "name": "Support Staff", "login": "support-staff@test", "group_ids": [(6, 0, [group_user.id])],
        })
        cls.other = cls.env["res.users"].create({
            "name": "Other Staff", "login": "support-other@test", "group_ids": [(6, 0, [group_user.id])],
        })
        cls.owner = cls.env["res.users"].create({
            "name": "Owner", "login": "support-owner@test",
            "group_ids": [(6, 0, [group_user.id, cls.env.ref("security_base.group_security_owner").id])],
        })
        cls.employee = cls.env["hr.employee"].create({"name": "Support Staff", "user_id": cls.staff.id})
        cls.task = cls.env["security.work.task"].create({"name": "Register attendance", "employee_id": cls.employee.id})

    def test_problem_report_scrubs_credentials_and_links_own_task(self):
        Req = self.env["security.support.request"].with_user(self.staff)
        res = Req.create_from_client({
            "subject": "  Can't capture attendance  ",
            "client_category": "not_working",
            "priority": "3",
            "route": "/work",
            "work_task_id": self.task.id,
            "diagnostics": {"route": "/work", "session_id": "SECRET", "nested": {"password": "hunter2", "ok": 1}},
        })
        rec = Req.browse(res["id"])
        self.assertTrue(rec.name.startswith("SUPP/"))
        self.assertEqual(rec.subject, "Can't capture attendance")
        self.assertEqual(rec.work_task_id, self.task)
        diag = json.loads(rec.diagnostics)
        self.assertNotIn("session_id", diag)
        self.assertNotIn("password", diag["nested"])
        self.assertNotIn("SECRET", rec.diagnostics)

    def test_problem_report_needs_a_summary(self):
        with self.assertRaises(UserError):
            self.env["security.support.request"].with_user(self.staff).create_from_client({"subject": "  "})

    def test_staff_see_only_their_own_reports(self):
        mine = self.env["security.support.request"].with_user(self.staff).create_from_client({"subject": "mine"})
        self.env["security.support.request"].with_user(self.other).create_from_client({"subject": "theirs"})
        visible = self.env["security.support.request"].with_user(self.staff).search([])
        self.assertEqual(visible.ids, [mine["id"]])
        self.assertEqual(len(self.env["security.support.request"].with_user(self.owner).search([])), 2)

    def test_feedback_only_on_a_task_you_can_see(self):
        Fb = self.env["security.task.feedback"]
        self.assertEqual(Fb.with_user(self.staff).submit_feedback({"task_id": self.task.id, "rating": "easy"})["rating"], "easy")
        with self.assertRaises(UserError):
            Fb.with_user(self.other).submit_feedback({"task_id": self.task.id, "rating": "easy"})

    def test_owner_overview_is_evidence_backed_and_restricted(self):
        with self.assertRaises(AccessError):
            self.env["security.owner.digest"].with_user(self.staff).get_owner_overview()
        data = self.env["security.owner.digest"].with_user(self.owner).get_owner_overview()
        keys = {t["key"] for t in data["tiles"]}
        self.assertTrue({"tasks_today", "overdue", "could_not_complete", "support"} <= keys)
        for tile in data["tiles"]:
            self.assertIn("model", tile["drill"])
            self.assertIsInstance(tile["drill"]["domain"], list)
            # The drill-down returns exactly the records the number counts.
            count = self.env[tile["drill"]["model"]].sudo().search_count(tile["drill"]["domain"])
            if tile["key"] != "tasks_today":
                self.assertEqual(count, tile["value"], tile["key"])

    def test_contextual_help_prefers_the_matching_workflow(self):
        cat = self.env["security.help.category"].create({"name": "Ops"})
        Art = self.env["security.help.article"]
        Art.create({"category_id": cat.id, "title": "General", "body": "<p>x</p>"})
        specific = Art.create({"category_id": cat.id, "title": "Attendance", "body": "<p>x</p>", "workflow_key": "attendance.post"})
        res = Art.with_user(self.staff).get_contextual_articles(route="/work", workflow_key="attendance.post", limit=2)
        self.assertEqual(res[0]["id"], specific.id)
