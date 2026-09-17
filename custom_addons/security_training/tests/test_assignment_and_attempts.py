from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAssignmentVersionPinning(TransactionCase):
    """docs/deployguard/BUILD-STATUS-AND-PHASE-PLAN.md Phase 4.2: a publish
    must not change an in-flight assignment."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = cls.env["res.users"].create({
            "name": "Pin Test Author", "login": "pin-test-author@access-control.test",
            "group_ids": [(6, 0, [cls.env.ref("security_training.group_training_supervisor").id])],
        })
        cls.employee = cls.env["hr.employee"].create({"name": "Pin Test Guard"})

    def _published_version(self, course_name, section_name):
        env = self.env.with_user(self.author)
        course = env["security.training.course"].create({"name": course_name})
        version = course.version_ids
        env["security.training.section"].create({"course_version_id": version.id, "name": section_name})
        version.action_submit_for_review()
        version.with_user(self.env.ref("base.user_admin")).action_approve()
        return course, version

    def test_assignment_pins_the_published_version(self):
        course, v1 = self._published_version("Pin Course", "S1")
        assignment = self.env["security.training.assignment"].create({
            "employee_id": self.employee.id, "course_id": course.id,
        })
        self.assertEqual(assignment.course_version_id, v1)

    def test_cannot_assign_a_course_with_no_published_version(self):
        course = self.env.with_user(self.author)["security.training.course"].create({"name": "Unpublished"})
        with self.assertRaises(UserError):
            self.env["security.training.assignment"].create({
                "employee_id": self.employee.id, "course_id": course.id,
            })

    def test_new_publish_does_not_change_existing_assignment(self):
        env = self.env.with_user(self.author)
        course, v1 = self._published_version("Repin Course", "S1")
        assignment = self.env["security.training.assignment"].create({
            "employee_id": self.employee.id, "course_id": course.id,
        })
        self.assertEqual(assignment.course_version_id, v1)

        v2 = env["security.training.course.version"].create({"course_id": course.id})
        env["security.training.section"].create({"course_version_id": v2.id, "name": "S1 v2"})
        v2.action_submit_for_review()
        v2.with_user(self.env.ref("base.user_admin")).action_approve()

        assignment.invalidate_recordset()
        self.assertEqual(
            assignment.course_version_id, v1,
            "an in-flight assignment must keep the version it was created against",
        )
        self.assertEqual(course.published_version_id, v2)


@tagged("post_install", "-at_install")
class TestAttemptScoring(TransactionCase):
    """Pass/fail paths and attempt limits, Phase 4.7."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        author = cls.env["res.users"].create({
            "name": "Attempt Test Author", "login": "attempt-test-author@access-control.test",
            "group_ids": [(6, 0, [cls.env.ref("security_training.group_training_supervisor").id])],
        })
        env = cls.env.with_user(author)
        cls.employee = cls.env["hr.employee"].create({"name": "Attempt Test Guard"})

        course = env["security.training.course"].create({"name": "Quiz Course"})
        version = course.version_ids
        env["security.training.section"].create({"course_version_id": version.id, "name": "S1"})
        cls.assessment = env["security.training.assessment"].create({
            "course_version_id": version.id, "name": "Quiz", "pass_mark_pct": 100.0, "max_attempts": 2,
        })
        cls.question = env["security.training.question"].create({
            "assessment_id": cls.assessment.id, "text": "2 + 2?", "question_type": "single",
        })
        cls.correct_option = env["security.training.question.option"].create({
            "question_id": cls.question.id, "text": "4", "is_correct": True,
        })
        cls.wrong_option = env["security.training.question.option"].create({
            "question_id": cls.question.id, "text": "5", "is_correct": False,
        })

        version.action_submit_for_review()
        version.with_user(cls.env.ref("base.user_admin")).action_approve()
        cls.assignment = cls.env["security.training.assignment"].create({
            "employee_id": cls.employee.id, "course_id": course.id,
        })

    def test_correct_answer_passes(self):
        attempt = self.env["security.training.attempt"].action_start_attempt(
            self.assignment.id, self.assessment.id
        )
        attempt.action_submit({self.question.id: [self.correct_option.id]})
        self.assertEqual(attempt.state, "passed")
        self.assertEqual(attempt.score_pct, 100.0)

    def test_wrong_answer_fails(self):
        attempt = self.env["security.training.attempt"].action_start_attempt(
            self.assignment.id, self.assessment.id
        )
        attempt.action_submit({self.question.id: [self.wrong_option.id]})
        self.assertEqual(attempt.state, "failed")
        self.assertEqual(attempt.score_pct, 0.0)

    def test_attempt_limit_is_enforced(self):
        Attempt = self.env["security.training.attempt"]
        a1 = Attempt.action_start_attempt(self.assignment.id, self.assessment.id)
        a1.action_submit({self.question.id: [self.wrong_option.id]})
        a2 = Attempt.action_start_attempt(self.assignment.id, self.assessment.id)
        a2.action_submit({self.question.id: [self.wrong_option.id]})
        with self.assertRaises(UserError):
            Attempt.action_start_attempt(self.assignment.id, self.assessment.id)

    def test_exhausting_attempts_fails_the_assignment(self):
        Attempt = self.env["security.training.attempt"]
        for _ in range(2):
            attempt = Attempt.action_start_attempt(self.assignment.id, self.assessment.id)
            attempt.action_submit({self.question.id: [self.wrong_option.id]})
        self.assignment.invalidate_recordset()
        self.assertEqual(self.assignment.state, "failed")

    def test_passing_completes_the_assignment_after_lessons_done(self):
        lesson = self.assignment.course_version_id.section_ids.lesson_ids
        if not lesson:
            lesson = self.env.with_user(
                self.env.ref("base.user_admin")
            )["security.training.lesson"].create({
                "section_id": self.assignment.course_version_id.section_ids[0].id, "name": "L1",
            })
        self.env["security.training.lesson.progress"].create({
            "assignment_id": self.assignment.id, "lesson_id": lesson[:1].id,
        })
        attempt = self.env["security.training.attempt"].action_start_attempt(
            self.assignment.id, self.assessment.id
        )
        attempt.action_submit({self.question.id: [self.correct_option.id]})
        self.assignment.invalidate_recordset()
        self.assertEqual(self.assignment.state, "completed")

    def test_completing_the_assignment_grants_a_competency(self):
        lesson = self.env.with_user(
            self.env.ref("base.user_admin")
        )["security.training.lesson"].create({
            "section_id": self.assignment.course_version_id.section_ids[0].id, "name": "L1",
        })
        self.env["security.training.lesson.progress"].create({
            "assignment_id": self.assignment.id, "lesson_id": lesson.id,
        })
        attempt = self.env["security.training.attempt"].action_start_attempt(
            self.assignment.id, self.assessment.id
        )
        attempt.action_submit({self.question.id: [self.correct_option.id]})
        competency = self.env["security.training.competency"].search(
            [("assignment_id", "=", self.assignment.id)]
        )
        self.assertTrue(competency)
