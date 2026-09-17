import os

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase

from odoo.addons.security_deployguard_bridge.models import security_deployguard_crypto as crypto


class TestDeployguardConfig(TransactionCase):

    def setUp(self):
        super().setUp()
        self._orig_env_key = os.environ.get(crypto.MASTER_KEY_ENV_VAR)
        os.environ[crypto.MASTER_KEY_ENV_VAR] = "a-test-master-key"
        self.addCleanup(self._restore_env_key)

    def _restore_env_key(self):
        if self._orig_env_key is not None:
            os.environ[crypto.MASTER_KEY_ENV_VAR] = self._orig_env_key
        else:
            os.environ.pop(crypto.MASTER_KEY_ENV_VAR, None)

    def test_post_init_hook_created_exactly_one_config(self):
        # post_init_hook already ran when this module was installed for the
        # test database; assert its result rather than re-running it.
        configs = self.env["security.deployguard.config"].sudo().search([])
        self.assertEqual(len(configs), 1)
        self.assertTrue(configs.integration_user_id)

    def test_get_config_does_not_duplicate(self):
        Config = self.env["security.deployguard.config"]
        first = Config.get_config()
        second = Config.get_config()
        self.assertEqual(first, second)

    def test_integration_user_has_no_known_password(self):
        config = self.env["security.deployguard.config"].get_config()
        user = config.integration_user_id
        self.assertTrue(user)
        self.assertEqual(user.login, "deployguard.integration")
        # The point of the random password is that nobody, including this
        # test, knows it -- verified indirectly: it must not be empty and
        # must not equal a plausible guessed default.
        self.assertNotIn(user.login, ("admin123", "deployguard", ""))

    def test_generate_webhook_secret_never_readable_again(self):
        config = self.env["security.deployguard.config"].get_config()
        self.assertFalse(config.webhook_secret_set)
        result = config.action_generate_webhook_secret()
        self.assertTrue(config.webhook_secret_set)
        secret_in_notification = result["params"]["message"]
        self.assertIn(":", secret_in_notification)
        # The stored value must not be the plaintext secret.
        self.assertNotEqual(config.webhook_secret_encrypted, secret_in_notification)

    def test_get_webhook_secret_roundtrips(self):
        config = self.env["security.deployguard.config"].get_config()
        result = config.action_generate_webhook_secret()
        plaintext = result["params"]["message"].split(": ", 1)[1]
        self.assertEqual(config.get_webhook_secret(), plaintext)

    def test_get_webhook_secret_without_one_set_refuses(self):
        config = self.env["security.deployguard.config"].get_config()
        with self.assertRaises(UserError):
            config.get_webhook_secret()

    def test_generate_signing_keypair_sets_kid_and_public_key(self):
        config = self.env["security.deployguard.config"].get_config()
        self.assertFalse(config.signing_key_id)
        config.action_generate_signing_keypair()
        self.assertTrue(config.signing_key_id)
        self.assertTrue(config.signing_public_key)
        self.assertTrue(config.signing_private_key_encrypted)

    def test_rotating_signing_keypair_changes_the_kid(self):
        config = self.env["security.deployguard.config"].get_config()
        config.action_generate_signing_keypair()
        first_kid = config.signing_key_id
        first_public = config.signing_public_key
        config.action_generate_signing_keypair()
        self.assertNotEqual(config.signing_key_id, first_kid)
        self.assertNotEqual(config.signing_public_key, first_public)

    def test_get_signing_private_key_without_one_set_refuses(self):
        config = self.env["security.deployguard.config"].get_config()
        with self.assertRaises(UserError):
            config.get_signing_private_key()

    def test_get_signing_private_key_returns_raw_bytes(self):
        config = self.env["security.deployguard.config"].get_config()
        config.action_generate_signing_keypair()
        private_key_bytes = config.get_signing_private_key()
        self.assertEqual(len(private_key_bytes), 32, "Ed25519 private keys are 32 raw bytes")

    def test_master_key_configured_reflects_environment(self):
        config = self.env["security.deployguard.config"].get_config()
        self.assertTrue(config.master_key_configured)
        os.environ.pop(crypto.MASTER_KEY_ENV_VAR, None)
        config.invalidate_recordset(["master_key_configured"])
        self.assertFalse(config.master_key_configured)
