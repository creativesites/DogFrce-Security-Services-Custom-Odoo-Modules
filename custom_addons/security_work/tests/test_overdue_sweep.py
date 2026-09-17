from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOverdueSweep(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env["res.users"].create({
            "name": "Overdue Sweep Guard", "login": "overdue-sweep-guard@access-control.test",
            "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
        })
        cls.employee = cls.env["hr.employee"].create({
            "name": "Overdue Sweep Guard", "user_id": cls.user.id,
        })

    def _overdue_task(self):
        return self.env["security.work.task"].create({
            "name": "Overdue Task", "employee_id": self.employee.id,
            "due_at": "2020-01-01 09:00:00", "state": "open",
        })

    def test_overdue_task_gets_flagged(self):
        task = self._overdue_task()
        self.env["security.work.task"].action_sweep_overdue()
        self.assertTrue(task.overdue_flagged_at)

    def test_overdue_task_gets_a_chatter_note(self):
        task = self._overdue_task()
        self.env["security.work.task"].action_sweep_overdue()
        self.assertTrue(any("Overdue" in (b or "") for b in task.message_ids.mapped("body")))

    def test_overdue_task_gets_an_activity(self):
        task = self._overdue_task()
        self.env["security.work.task"].action_sweep_overdue()
        self.assertTrue(task.activity_ids)

    def test_flagged_task_is_not_reflagged(self):
        task = self._overdue_task()
        self.env["security.work.task"].action_sweep_overdue()
        first_flagged_at = task.overdue_flagged_at
        self.env["security.work.task"].action_sweep_overdue()
        self.assertEqual(task.overdue_flagged_at, first_flagged_at)

    def test_task_due_in_the_future_is_not_flagged(self):
        task = self.env["security.work.task"].create({
            "name": "Future Task", "employee_id": self.employee.id,
            "due_at": "2099-01-01 09:00:00", "state": "open",
        })
        self.env["security.work.task"].action_sweep_overdue()
        self.assertFalse(task.overdue_flagged_at)

    def test_verified_task_is_never_flagged_even_if_due_date_passed(self):
        task = self.env["security.work.task"].create({
            "name": "Verified Task", "employee_id": self.employee.id,
            "due_at": "2020-01-01 09:00:00", "state": "verified",
        })
        self.env["security.work.task"].action_sweep_overdue()
        self.assertFalse(task.overdue_flagged_at)
