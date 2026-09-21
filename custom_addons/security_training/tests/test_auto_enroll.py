from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAutoEnroll(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        supervisor = cls.env.ref("security_training.group_training_supervisor")
        cls.author = cls.env["res.users"].create({
            "name": "Enrol Author", "login": "enrol-author@access-control.test",
            "group_ids": [(6, 0, [supervisor.id])],
        })
        cls.approver = cls.env["res.users"].create({
            "name": "Enrol Approver", "login": "enrol-approver@access-control.test",
            "group_ids": [(6, 0, [supervisor.id])],
        })
        cls.role = cls.env["res.groups"].create({"name": "Enrol Test Role"})
        internal = cls.env.ref("base.group_user")

        cls.user_in_role = cls.env["res.users"].create({
            "name": "In Role", "login": "enrol-in-role@access-control.test",
            "group_ids": [(6, 0, [internal.id, cls.role.id])],
        })
        cls.user_plain = cls.env["res.users"].create({
            "name": "Plain", "login": "enrol-plain@access-control.test",
            "group_ids": [(6, 0, [internal.id])],
            "tz": "Africa/Windhoek",
        })
        cls.user_portal = cls.env["res.users"].create({
            "name": "Portal", "login": "enrol-portal@access-control.test",
            "group_ids": [(6, 0, [cls.env.ref("base.group_portal").id])],
        })

        Employee = cls.env["hr.employee"]
        cls.emp_in_role = Employee.create({"name": "Emp In Role", "user_id": cls.user_in_role.id})
        cls.emp_plain = Employee.create({"name": "Emp Plain", "user_id": cls.user_plain.id})
        cls.emp_no_login = Employee.create({"name": "Emp No Login"})
        cls.emp_portal = Employee.create({"name": "Emp Portal", "user_id": cls.user_portal.id})

    def _course(self, publish=True, **vals):
        env = self.env(user=self.author)
        course = env["security.training.course"].create({"name": "Enrol Course", **vals})
        version = env["security.training.course.version"].create({"course_id": course.id})
        env["security.training.section"].create({"course_version_id": version.id, "name": "S1"})
        if publish:
            version.action_submit_for_review()
            version.with_user(self.approver).action_approve()
        return course

    def _assigned(self, course):
        return self.env["security.training.assignment"].search([("course_id", "=", course.id)]).employee_id

    def test_publish_enrols_only_people_who_can_open_the_app(self):
        course = self._course(auto_enroll=True)
        assigned = self._assigned(course)
        self.assertIn(self.emp_in_role, assigned)
        self.assertIn(self.emp_plain, assigned)
        self.assertNotIn(self.emp_no_login, assigned)
        self.assertNotIn(self.emp_portal, assigned)

    def test_role_filter_narrows_enrolment(self):
        course = self._course(auto_enroll=True, auto_enroll_group_ids=[(6, 0, [self.role.id])])
        assigned = self._assigned(course)
        self.assertIn(self.emp_in_role, assigned)
        self.assertNotIn(self.emp_plain, assigned)

    def test_off_by_default(self):
        course = self._course()
        self.assertFalse(self._assigned(course))

    def test_turning_it_on_enrols_an_already_published_course(self):
        course = self._course()
        course.write({"auto_enroll": True})
        self.assertIn(self.emp_plain, self._assigned(course))

    def test_idempotent_and_never_reassigns_a_finished_course(self):
        course = self._course(auto_enroll=True)
        Assignment = self.env["security.training.assignment"]
        mine = Assignment.search([("course_id", "=", course.id), ("employee_id", "=", self.emp_plain.id)])
        mine.write({"state": "completed"})
        course._auto_enroll()
        course._auto_enroll()
        self.assertEqual(
            Assignment.search_count([("course_id", "=", course.id), ("employee_id", "=", self.emp_plain.id)]),
            1,
        )

    def test_due_date_counts_from_the_learners_own_local_date(self):
        course = self._course(auto_enroll=True, enroll_due_days=14)
        assignment = self.env["security.training.assignment"].search([
            ("course_id", "=", course.id), ("employee_id", "=", self.emp_plain.id),
        ])
        learner_today = fields.Date.context_today(
            self.env["security.training.course"].with_context(tz="Africa/Windhoek")
        )
        self.assertEqual(assignment.due_date, fields.Date.add(learner_today, days=14))

    def test_zero_due_days_means_no_due_date(self):
        course = self._course(auto_enroll=True, enroll_due_days=0)
        assignment = self.env["security.training.assignment"].search([
            ("course_id", "=", course.id), ("employee_id", "=", self.emp_plain.id),
        ])
        self.assertFalse(assignment.due_date)

    def test_hourly_sweep_picks_up_a_new_hire(self):
        course = self._course(auto_enroll=True)
        new_user = self.env["res.users"].create({
            "name": "New Hire", "login": "enrol-new-hire@access-control.test",
            "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
        })
        new_hire = self.env["hr.employee"].create({"name": "New Hire", "user_id": new_user.id})
        self.assertNotIn(new_hire, self._assigned(course))
        self.env["security.training.course"]._cron_auto_enroll()
        self.assertIn(new_hire, self._assigned(course))
