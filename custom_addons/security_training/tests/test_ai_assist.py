from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestLessonAiAssist(TransactionCase):
    """The AI assist is optional and must fail cleanly, never crash, when
    security_ai_engine isn't installed or has no key configured -- see
    ask_ai's own docstring for why this exists at all (a deliberate,
    narrow exception to the MVP's no-AI scope guard)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        author = cls.env["res.users"].create({
            "name": "AI Assist Test Author", "login": "ai-assist-test-author@access-control.test",
            "group_ids": [(6, 0, [cls.env.ref("security_training.group_training_supervisor").id])],
        })
        env = cls.env(user=author)
        course = env["security.training.course"].create({"name": "AI Assist Test Course"})
        version = course.version_ids[:1] or env["security.training.course.version"].create({"course_id": course.id})
        section = env["security.training.section"].create({
            "course_version_id": version.id, "name": "S1",
        })
        cls.lesson = env["security.training.lesson"].create({
            "section_id": section.id, "name": "L1", "body": "<p>Click Save.</p>",
        })

    def test_ask_ai_fails_cleanly_without_the_ai_engine(self):
        # security_ai_engine is not a dependency of security_training and
        # is very unlikely to be installed in a test database that only
        # installs security_training's own dependency closure.
        if "security.ai.config" in self.env:
            self.skipTest("security_ai_engine happens to be installed in this test database")
        with self.assertRaises(UserError):
            self.lesson.ask_ai("What do I click?")

    def test_deep_link_path_is_optional(self):
        self.assertFalse(self.lesson.deep_link_path)
        self.lesson.deep_link_path = "/odoo/action-some_module.some_action"
        self.assertTrue(self.lesson.deep_link_path)
