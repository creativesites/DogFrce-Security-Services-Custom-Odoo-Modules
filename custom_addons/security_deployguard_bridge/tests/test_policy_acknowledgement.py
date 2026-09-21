from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.security_deployguard_bridge.models.security_deployguard_policy_acknowledgement import (
    NOTICE_VERSION,
)


@tagged("post_install", "-at_install")
class TestPolicyAcknowledgement(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        internal = cls.env.ref("base.group_user")
        cls.alice = cls.env["res.users"].create({
            "name": "Alice Ack", "login": "alice-ack@access-control.test",
            "group_ids": [(6, 0, [internal.id])],
        })
        cls.bob = cls.env["res.users"].create({
            "name": "Bob Ack", "login": "bob-ack@access-control.test",
            "group_ids": [(6, 0, [internal.id])],
        })

    def _model(self, user):
        return self.env(user=user)["security.deployguard.policy.acknowledgement"]

    def test_not_acknowledged_until_the_person_does_it(self):
        notice = self._model(self.alice).get_notice()
        self.assertEqual(notice["version"], NOTICE_VERSION)
        self.assertFalse(notice["acknowledged"])
        self.assertTrue(notice["body"])

    def test_acknowledging_records_it_for_the_caller_only(self):
        result = self._model(self.alice).acknowledge(NOTICE_VERSION, client="test")
        self.assertTrue(result["acknowledged"])
        self.assertFalse(self._model(self.bob).get_notice()["acknowledged"])
        ack = self.env["security.deployguard.policy.acknowledgement"].search([
            ("notice_version", "=", NOTICE_VERSION), ("user_id", "=", self.alice.id),
        ])
        self.assertEqual(len(ack), 1)
        self.assertEqual(ack.client, "test")

    def test_acknowledging_twice_keeps_one_record(self):
        self._model(self.alice).acknowledge(NOTICE_VERSION)
        self._model(self.alice).acknowledge(NOTICE_VERSION)
        self.assertEqual(
            self.env["security.deployguard.policy.acknowledgement"].search_count([
                ("user_id", "=", self.alice.id),
            ]),
            1,
        )

    def test_refuses_to_record_agreement_to_text_that_was_not_shown(self):
        with self.assertRaises(UserError):
            self._model(self.alice).acknowledge("some-older-version")

    def test_employees_cannot_see_each_others_acknowledgements(self):
        self._model(self.alice).acknowledge(NOTICE_VERSION)
        self.assertFalse(self._model(self.bob).search([("user_id", "=", self.alice.id)]))

    def test_employees_cannot_create_one_directly(self):
        with self.assertRaises(AccessError):
            self._model(self.bob).create({"user_id": self.alice.id, "notice_version": NOTICE_VERSION})
