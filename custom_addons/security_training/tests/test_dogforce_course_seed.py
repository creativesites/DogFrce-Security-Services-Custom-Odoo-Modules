from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDogforceCourseSeed(TransactionCase):
    """Sanity checks on the real, seeded first course
    (data/security_training_dogforce_course.xml) -- not a workflow test,
    just confirming the content actually loaded and is assignable."""

    def test_course_exists_and_is_published(self):
        course = self.env.ref("security_training.course_getting_live")
        self.assertTrue(course.published_version_id)
        self.assertEqual(course.published_version_id.state, "published")

    def test_course_has_all_six_sections(self):
        course = self.env.ref("security_training.course_getting_live")
        self.assertEqual(len(course.published_version_id.section_ids), 6)

    def test_course_has_twelve_lessons(self):
        course = self.env.ref("security_training.course_getting_live")
        lessons = course.published_version_id.section_ids.mapped("lesson_ids")
        self.assertEqual(len(lessons), 12)

    def test_do_it_lessons_have_deep_links(self):
        do_it_lessons = self.env["security.training.lesson"].search([
            ("name", "like", "Do It:"),
        ])
        self.assertEqual(len(do_it_lessons), 5)
        self.assertTrue(all(lesson.deep_link_path for lesson in do_it_lessons))

    def test_assessment_has_five_questions_with_a_correct_answer_each(self):
        assessment = self.env.ref("security_training.assessment_getting_live")
        self.assertEqual(len(assessment.question_ids), 5)
        for question in assessment.question_ids:
            self.assertTrue(
                question.option_ids.filtered("is_correct"),
                f"question '{question.text}' has no correct option marked",
            )

    def test_course_can_actually_be_assigned(self):
        course = self.env.ref("security_training.course_getting_live")
        employee = self.env["hr.employee"].create({"name": "Course Seed Test Guard"})
        assignment = self.env["security.training.assignment"].create({
            "employee_id": employee.id, "course_id": course.id,
        })
        self.assertEqual(assignment.course_version_id, course.published_version_id)

    def test_all_twelve_lessons_have_detailed_body(self):
        course = self.env.ref("security_training.course_getting_live")
        lessons = course.published_version_id.section_ids.mapped("lesson_ids")
        self.assertEqual(len(lessons), 12)
        for lesson in lessons:
            self.assertTrue(
                lesson.body and len(lesson.body.strip()) > 50,
                f"lesson '{lesson.name}' has empty or insufficient body text",
            )

    def test_bulk_assign_active_employees(self):
        course = self.env.ref("security_training.course_getting_live")
        version = course.published_version_id
        emp1 = self.env["hr.employee"].create({"name": "Bulk Test Guard 1", "active": True})
        emp2 = self.env["hr.employee"].create({"name": "Bulk Test Guard 2", "active": True})
        res = version.action_assign_active_employees()
        self.assertEqual(res.get("type"), "ir.actions.client")
        assignments = self.env["security.training.assignment"].search([
            ("employee_id", "in", [emp1.id, emp2.id]),
            ("course_id", "=", course.id),
        ])
        self.assertEqual(len(assignments), 2)
