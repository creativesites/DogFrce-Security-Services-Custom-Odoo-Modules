from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestWorkTaskLifecycle(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_a = cls._create_internal_user("work-guard-a@access-control.test", "Work Guard A")
        cls.user_b = cls._create_internal_user("work-guard-b@access-control.test", "Work Guard B")

        cls.employee_a = cls.env["hr.employee"].create({
            "name": "Work Guard A",
            "security_guard": True,
            "user_id": cls.user_a.id,
        })
        cls.employee_b = cls.env["hr.employee"].create({
            "name": "Work Guard B",
            "security_guard": True,
            "user_id": cls.user_b.id,
        })

        cls.supervisor_user = cls._create_internal_user(
            "work-supervisor@access-control.test", "Work Test Supervisor"
        )
        cls.supervisor_user.write({
            "group_ids": [(4, cls.env.ref("security_work.group_work_supervisor").id)],
        })

        cls.template = cls.env["security.work.checklist.template"].create({
            "name": "Test Checklist",
            "code": "test.checklist",
            "item_ids": [
                (0, 0, {"label": "Required text item", "item_type": "text", "required": True}),
                (0, 0, {"label": "Optional bool item", "item_type": "boolean", "required": False}),
            ],
        })

    @classmethod
    def _create_internal_user(cls, login, name):
        return cls.env["res.users"].create({
            "name": name,
            "login": login,
            "email": login,
            "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
        })

    def _create_task(self, employee, **kwargs):
        vals = {"name": "Test task", "employee_id": employee.id}
        vals.update(kwargs)
        return self.env["security.work.task"].with_user(self.supervisor_user).create(vals)

    def test_default_state_is_open(self):
        task = self._create_task(self.employee_a)
        self.assertEqual(task.state, "open")

    def test_full_happy_path(self):
        task = self._create_task(self.employee_a)
        task = task.with_user(self.user_a)
        task.action_start()
        self.assertEqual(task.state, "in_progress")
        task.action_submit()
        self.assertEqual(task.state, "submitted")
        task.with_user(self.supervisor_user).action_verify()
        self.assertEqual(task.state, "verified")
        self.assertEqual(task.verified_by_id, self.supervisor_user)

    def test_cannot_verify_from_open(self):
        task = self._create_task(self.employee_a)
        with self.assertRaises(UserError):
            task.with_user(self.supervisor_user).action_verify()

    def test_reject_returns_to_in_progress(self):
        task = self._create_task(self.employee_a)
        task.with_user(self.user_a).action_submit()
        task.with_user(self.supervisor_user).action_reject("Missing signature")
        self.assertEqual(task.state, "in_progress")
        self.assertEqual(task.reject_reason, "Missing signature")

    def test_could_not_complete_requires_reason(self):
        task = self._create_task(self.employee_a)
        with self.assertRaises(UserError):
            task.with_user(self.user_a).action_could_not_complete(reason=None)

    def test_could_not_complete_records_reason(self):
        task = self._create_task(self.employee_a)
        task.with_user(self.user_a).action_could_not_complete(reason="site_access", note="Gate locked")
        self.assertEqual(task.state, "could_not_complete")
        self.assertEqual(task.cnc_reason, "site_access")

    def test_reopen_from_could_not_complete(self):
        task = self._create_task(self.employee_a)
        task.with_user(self.user_a).action_could_not_complete(reason="other")
        task.with_user(self.supervisor_user).action_reopen()
        self.assertEqual(task.state, "open")

    def test_submit_blocked_by_unanswered_required_item(self):
        task = self._create_task(self.employee_a, checklist_template_id=self.template.id)
        with self.assertRaises(UserError):
            task.with_user(self.user_a).action_submit()

    def test_submit_succeeds_once_required_item_answered(self):
        task = self._create_task(self.employee_a, checklist_template_id=self.template.id)
        required_response = task.response_ids.filtered(lambda r: r.item_def_id.required)
        required_response.value_text = "Done"
        task.with_user(self.user_a).action_submit()
        self.assertEqual(task.state, "submitted")

    def test_checklist_responses_created_from_template(self):
        task = self._create_task(self.employee_a, checklist_template_id=self.template.id)
        self.assertEqual(len(task.response_ids), 2)


@tagged("post_install", "-at_install")
class TestWorkTaskAccessControl(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_a = cls.env["res.users"].create({
            "name": "Work Guard A",
            "login": "work-access-a@access-control.test",
            "email": "work-access-a@access-control.test",
            "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
        })
        cls.user_b = cls.env["res.users"].create({
            "name": "Work Guard B",
            "login": "work-access-b@access-control.test",
            "email": "work-access-b@access-control.test",
            "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
        })
        cls.employee_a = cls.env["hr.employee"].create({
            "name": "Work Guard A", "security_guard": True, "user_id": cls.user_a.id,
        })
        cls.employee_b = cls.env["hr.employee"].create({
            "name": "Work Guard B", "security_guard": True, "user_id": cls.user_b.id,
        })
        cls.task_b = cls.env["security.work.task"].create({
            "name": "B's task", "employee_id": cls.employee_b.id,
        })

    def test_user_cannot_see_another_employees_task(self):
        tasks = self.env["security.work.task"].with_user(self.user_a).search([("id", "=", self.task_b.id)])
        self.assertFalse(tasks, "A regular user could see another employee's work task.")

    def test_user_cannot_create_task(self):
        with self.assertRaises(AccessError):
            self.env["security.work.task"].with_user(self.user_a).create({
                "name": "Self-assigned", "employee_id": self.employee_a.id,
            })
