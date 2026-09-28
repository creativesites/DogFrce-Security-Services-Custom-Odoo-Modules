from datetime import date

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


class TestRosterSignoff(TransactionCase):
    """Sign-offs must record accountability without ever gating the roster."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({
            "name": "Test Client", "is_company": True,
        })
        cls.batch = cls.env["security.roster.batch"].create({
            "partner_id": cls.partner.id,
            "date_from": date(2026, 10, 1),
            "date_to": date(2026, 10, 31),
        })

    def test_signoffs_are_created_for_every_role(self):
        self.batch._ensure_signoffs()
        self.assertEqual(len(self.batch.signoff_ids), 5)
        self.assertEqual(
            set(self.batch.signoff_ids.mapped("role")),
            {"front_desk", "general_manager", "hr", "finance", "director"},
        )
        self.assertTrue(all(s.state == "pending" for s in self.batch.signoff_ids))

    def test_ensure_signoffs_is_idempotent(self):
        self.batch._ensure_signoffs()
        self.batch._ensure_signoffs()
        self.assertEqual(len(self.batch.signoff_ids), 5)

    def test_pending_signoffs_do_not_block_the_roster(self):
        """The whole point: a roster with nobody signed off still confirms."""
        self.batch._ensure_signoffs()
        self.assertEqual(self.batch.signoff_pending_count, 5)
        self.batch.action_confirm()
        self.assertEqual(self.batch.state, "confirmed")

    def test_flagged_signoff_does_not_block_the_roster(self):
        self.batch._ensure_signoffs()
        signoff = self.batch.signoff_ids.filtered(lambda s: s.role == "front_desk")
        signoff.write({"state": "flagged", "note": "Night shift looks short"})
        self.batch.action_confirm()
        self.assertEqual(self.batch.state, "confirmed")
        self.assertEqual(self.batch.signoff_flagged_count, 1)

    def test_summary_names_who_it_waits_on(self):
        self.batch._ensure_signoffs()
        self.batch.signoff_ids.write({"state": "signed"})
        self.batch.signoff_ids.filtered(lambda s: s.role == "hr").write({"state": "pending"})
        self.assertIn("HR", self.batch.signoff_summary)

    def test_summary_when_all_signed(self):
        self.batch._ensure_signoffs()
        self.batch.signoff_ids.write({"state": "signed"})
        self.assertEqual(self.batch.signoff_summary, "All roles signed off")

    def test_cannot_sign_for_a_role_you_do_not_hold(self):
        self.batch._ensure_signoffs()
        finance = self.batch.signoff_ids.filtered(lambda s: s.role == "finance")

        user = self.env["res.users"].create({
            "name": "Ordinary User",
            "login": "ordinary_user_signoff_test",
            "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
        })
        with self.assertRaises(UserError):
            finance.with_user(user).action_sign()

    def test_flagging_requires_a_reason(self):
        self.batch._ensure_signoffs()
        director = self.batch.signoff_ids.filtered(lambda s: s.role == "director")
        # The test user is an admin, so it holds the Owner-implied director role.
        if director.can_sign:
            with self.assertRaises(UserError):
                director.action_flag()

    def test_one_row_per_role(self):
        self.batch._ensure_signoffs()
        roles = self.batch.signoff_ids.mapped("role")
        self.assertEqual(len(roles), len(set(roles)))


@tagged("post_install", "-at_install")
class TestRosterApprovalRoles(TransactionCase):
    """DogForce roles matrix (2026-09-28): HR and the GM approve rosters;
    the Operations Supervisor who drafts them does not."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        base = cls.env.ref("base.group_user")
        hr_user = cls.env.ref("hr.group_hr_user")

        def user(login, group):
            return cls.env["res.users"].create({
                "name": login, "login": login,
                "group_ids": [(6, 0, [base.id, hr_user.id, cls.env.ref(group).id])],
            })

        cls.ops = user("roster-ops@test", "security_base.group_security_supervisor")
        cls.hr = user("roster-hr@test", "security_base.group_security_hr_payroll_officer")
        cls.gm = user("roster-gm@test", "security_base.group_security_manager")
        cls.owner = user("roster-owner@test", "security_base.group_security_owner")

    def _batch(self):
        partner = self.env["res.partner"].create({"name": "Approval Client", "is_company": True})
        batch = self.env["security.roster.batch"].create({
            "partner_id": partner.id, "date_from": date(2026, 10, 1), "date_to": date(2026, 10, 31),
        })
        batch.state = "submitted"
        return batch

    def test_supervisor_cannot_approve(self):
        batch = self._batch()
        with self.assertRaises(UserError):
            batch.with_user(self.ops).action_approve()

    def test_hr_gm_and_owner_can_approve(self):
        for approver in (self.hr, self.gm, self.owner):
            batch = self._batch()
            batch.with_user(approver).action_approve()
            self.assertEqual(batch.state, "approved")
