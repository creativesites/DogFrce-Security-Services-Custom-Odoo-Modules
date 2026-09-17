from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCourseAuthoring(TransactionCase):
    """docs/deployguard/BUILD-STATUS-AND-PHASE-PLAN.md Phase 4.7: authoring
    permissions and the draft -> review -> publish workflow."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = cls.env["res.users"].create({
            "name": "Training Author", "login": "training-author@access-control.test",
            "group_ids": [(6, 0, [cls.env.ref("security_training.group_training_supervisor").id])],
        })
        cls.approver = cls.env["res.users"].create({
            "name": "Training Approver", "login": "training-approver@access-control.test",
            "group_ids": [(6, 0, [cls.env.ref("security_training.group_training_supervisor").id])],
        })
        cls.plain_user = cls.env["res.users"].create({
            "name": "Plain Training User", "login": "training-plain@access-control.test",
            "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
        })

    def _course_with_one_section(self, user=None):
        env = self.env if user is None else self.env.with_user(user)
        course = env["security.training.course"].create({"name": "Test Course"})
        version = course.version_ids[:1] or env["security.training.course.version"].create({
            "course_id": course.id
        })
        env["security.training.section"].create({
            "course_version_id": version.id, "name": "Section 1",
        })
        return course, version

    def test_first_version_is_auto_numbered_one(self):
        _course, version = self._course_with_one_section(self.author)
        self.assertEqual(version.version_number, 1)

    def test_plain_user_cannot_create_a_course(self):
        with self.assertRaises(AccessError):
            self.env["security.training.course"].with_user(self.plain_user).create({"name": "Nope"})

    def test_cannot_submit_review_without_a_section(self):
        env = self.env.with_user(self.author)
        course = env["security.training.course"].create({"name": "Empty Course"})
        version = env["security.training.course.version"].create({"course_id": course.id})
        with self.assertRaises(UserError):
            version.action_submit_for_review()

    def test_cannot_approve_your_own_submission(self):
        _course, version = self._course_with_one_section(self.author)
        version.with_user(self.author).action_submit_for_review()
        with self.assertRaises(UserError):
            version.with_user(self.author).action_approve()

    def test_a_different_supervisor_can_approve(self):
        _course, version = self._course_with_one_section(self.author)
        version.with_user(self.author).action_submit_for_review()
        version.with_user(self.approver).action_approve()
        self.assertEqual(version.state, "published")

    def test_plain_user_cannot_approve(self):
        _course, version = self._course_with_one_section(self.author)
        version.with_user(self.author).action_submit_for_review()
        with self.assertRaises(UserError):
            version.with_user(self.plain_user).action_approve()

    def test_publishing_a_new_version_archives_the_old_one(self):
        course, v1 = self._course_with_one_section(self.author)
        v1.with_user(self.author).action_submit_for_review()
        v1.with_user(self.approver).action_approve()

        v2 = self.env.with_user(self.author)["security.training.course.version"].create({
            "course_id": course.id
        })
        self.env.with_user(self.author)["security.training.section"].create({
            "course_version_id": v2.id, "name": "Section 1 (v2)",
        })
        v2.with_user(self.author).action_submit_for_review()
        v2.with_user(self.approver).action_approve()

        v1.invalidate_recordset()
        self.assertEqual(v1.state, "archived")
        self.assertEqual(v2.state, "published")
        self.assertEqual(course.published_version_id, v2)

    def test_plain_user_only_sees_published_versions(self):
        _course, version = self._course_with_one_section(self.author)
        found = self.env["security.training.course.version"].with_user(self.plain_user).search(
            [("id", "=", version.id)]
        )
        self.assertFalse(found, "a draft version must not be visible to a plain user")

        version.with_user(self.author).action_submit_for_review()
        version.with_user(self.approver).action_approve()
        found = self.env["security.training.course.version"].with_user(self.plain_user).search(
            [("id", "=", version.id)]
        )
        self.assertEqual(found, version)
