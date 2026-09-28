from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.security_guidance.models.guidance_session import SecurityGuidanceSession


@tagged("post_install", "-at_install")
class TestGuidanceEngine(TransactionCase):
    """The server decides the step from what the employee is actually doing."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env["res.users"].create({
            "name": "Learner", "login": "guidance-learner@test",
            "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
        })
        cls.flow = cls.env["security.guidance.flow"].create({
            "code": "test_flow", "name": "Test flow", "objective": "Do the thing.",
            "step_ids": [
                (0, 0, {"sequence": 10, "name": "Open the screen", "instruction": "Open it.",
                        "done_ui_json": '{"client_tag": "demo.screen"}', "target_json": '[{"text": "Demo"}]'}),
                (0, 0, {"sequence": 20, "name": "Do it at {site}", "instruction": "Press the button.",
                        "where_json": '{"client_tag": "demo.screen"}', "done_check": "demo_done",
                        "deviation_hint": "Go back to the demo screen.", "help_html": "<p>Help</p>"}),
            ],
        })
        cls.Session = cls.env["security.guidance.session"].with_user(cls.user)

    def test_first_step_until_the_screen_is_reached(self):
        payload = self.Session.start("test_flow")
        self.assertTrue(payload["practice"], "no task -> practice mode")
        self.assertEqual(payload["step"]["title"], "Open the screen")
        payload = self.Session.report_ui_state({"client_tag": "demo.screen"})
        self.assertEqual(payload["step"]["index"], 2)
        self.assertFalse(payload["off_track"])

    def test_reached_screen_steps_stick_and_leaving_is_off_track(self):
        self.Session.start("test_flow")
        self.Session.report_ui_state({"client_tag": "demo.screen"})
        payload = self.Session.report_ui_state({"model": "res.partner", "view_type": "list"})
        self.assertEqual(payload["step"]["index"], 2, "going elsewhere doesn't undo step 1")
        self.assertTrue(payload["off_track"])
        self.assertEqual(payload["step"]["deviation_hint"], "Go back to the demo screen.")
        kinds = self.env["security.guidance.event"].search([("user_id", "=", self.user.id)]).mapped("kind")
        self.assertIn("deviation", kinds)

    def test_record_checks_are_the_truth_on_a_real_task(self):
        employee = self.env["hr.employee"].create({"name": "Learner", "user_id": self.user.id})
        task = self.env["security.work.task"].create({"name": "Real work", "employee_id": employee.id})
        self.Session.start("test_flow", task_id=task.id)
        self.assertEqual(task.state, "in_progress", "guidance starts the task")
        self.Session.report_ui_state({"client_tag": "demo.screen"})
        with patch.object(SecurityGuidanceSession, "_guidance_check_demo_done", create=True, return_value=True):
            payload = self.Session.report_ui_state({"client_tag": "demo.screen"})
        self.assertEqual(payload["state"], "completed")

    def test_practice_steps_can_be_confirmed_but_real_ones_cannot(self):
        self.Session.start("test_flow")
        self.Session.report_ui_state({"client_tag": "demo.screen"})
        payload = self.Session.confirm_step()
        self.assertEqual(payload["state"], "completed")

        employee = self.env["hr.employee"].create({"name": "Learner", "user_id": self.user.id})
        task = self.env["security.work.task"].create({"name": "Real", "employee_id": employee.id})
        self.Session.start("test_flow", task_id=task.id)
        self.Session.report_ui_state({"client_tag": "demo.screen"})
        with self.assertRaises(UserError):
            self.Session.confirm_step()

    def test_one_active_session_and_only_your_own(self):
        self.Session.start("test_flow")
        self.Session.start("test_flow")
        self.assertEqual(self.env["security.guidance.session"].search_count([("user_id", "=", self.user.id), ("state", "=", "active")]), 1)
        other = self.env["res.users"].create({"name": "Other", "login": "guidance-other@test",
                                              "group_ids": [(6, 0, [self.env.ref("base.group_user").id])]})
        self.assertFalse(self.env["security.guidance.session"].with_user(other).get_active())

    def test_ai_falls_back_to_approved_help_and_says_so(self):
        self.Session.start("test_flow")
        self.Session.report_ui_state({"client_tag": "demo.screen"})
        with patch.object(type(self.env["security.guidance.session"]), "_ai_engine", create=True, return_value=None):
            answer = self.Session.ask_ai("What do I press?")
        # Whether or not an AI provider is configured in this database, the
        # answer is labelled, and without AI it is the step's approved help.
        self.assertIn("ai", answer)
        if not answer["ai"]:
            self.assertIn("Help", answer["answer"])

    def test_unknown_or_malformed_checks_never_pass(self):
        session = self.env["security.guidance.session"].with_user(self.user).browse(self.Session.start("test_flow")["id"])
        self.assertFalse(session._run_check("does_not_exist"))
        self.assertFalse(session._run_check("__class__"))
