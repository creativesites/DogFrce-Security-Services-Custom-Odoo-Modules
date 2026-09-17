from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestAttendanceReviewGate(TransactionCase):
    """Front Desk validates daily posting; Operations cannot self-review.

    docs/ROSTERING_SIMPLIFICATION_PLAN.md §3/A7a. Before this gate,
    action_review had no permission check at all, so whoever captured a
    posting sheet could also "review" it in the same click.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Review Gate Client"})

        cls.ops_user = cls.env["res.users"].create({
            "name": "Ops User",
            "login": "review_gate_ops_user",
            "groups_id": [(6, 0, [cls.env.ref("hr.group_hr_user").id])],
        })
        cls.front_desk_user = cls.env["res.users"].create({
            "name": "Front Desk User",
            "login": "review_gate_front_desk_user",
            "groups_id": [(6, 0, [
                cls.env.ref("security_operations.group_security_front_desk").id
            ])],
        })
        cls.random_user = cls.env["res.users"].create({
            "name": "Random Internal User",
            "login": "review_gate_random_user",
            "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
        })

    def _batch(self, captured_by):
        return self.env["security.attendance.batch"].with_user(captured_by).create({
            "partner_id": self.partner.id,
            "state": "captured",
            "captured_by_id": captured_by.id,
        })

    def test_capturer_cannot_review_own_batch(self):
        batch = self._batch(self.front_desk_user)
        with self.assertRaises(UserError):
            batch.with_user(self.front_desk_user).action_review()

    def test_front_desk_can_review_someone_elses_batch(self):
        batch = self._batch(self.ops_user)
        batch.with_user(self.front_desk_user).action_review()
        self.assertEqual(batch.state, "reviewed")
        self.assertEqual(batch.reviewed_by_id, self.front_desk_user)

    def test_plain_user_without_front_desk_group_cannot_review(self):
        batch = self._batch(self.ops_user)
        with self.assertRaises(UserError):
            batch.with_user(self.random_user).action_review()

    def test_manager_can_review_even_though_not_front_desk(self):
        manager = self.env["res.users"].create({
            "name": "Ops Manager",
            "login": "review_gate_manager_user",
            "groups_id": [(6, 0, [
                self.env.ref("security_base.group_security_manager").id
            ])],
        })
        batch = self._batch(self.ops_user)
        batch.with_user(manager).action_review()
        self.assertEqual(batch.state, "reviewed")
