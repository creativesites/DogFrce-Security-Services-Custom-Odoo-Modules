import os

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase

from odoo.addons.security_deployguard_bridge.models import security_deployguard_crypto as crypto


class TestDeployguardCrypto(TransactionCase):
    """Encryption at rest must actually fail closed, never fall back to
    storing plaintext. DG-ADR-018 §6."""

    def setUp(self):
        super().setUp()
        self._orig_env_key = os.environ.pop(crypto.MASTER_KEY_ENV_VAR, None)
        self.addCleanup(self._restore_env_key)

    def _restore_env_key(self):
        if self._orig_env_key is not None:
            os.environ[crypto.MASTER_KEY_ENV_VAR] = self._orig_env_key
        else:
            os.environ.pop(crypto.MASTER_KEY_ENV_VAR, None)

    def test_encrypt_without_master_key_refuses(self):
        with self.assertRaises(UserError):
            crypto.encrypt("some-secret")

    def test_master_key_configured_reflects_env_var(self):
        self.assertFalse(crypto.master_key_configured())
        os.environ[crypto.MASTER_KEY_ENV_VAR] = "a-test-master-key"
        self.assertTrue(crypto.master_key_configured())

    def test_roundtrip_with_master_key(self):
        os.environ[crypto.MASTER_KEY_ENV_VAR] = "a-test-master-key"
        ciphertext = crypto.encrypt("correct horse battery staple")
        self.assertNotIn("correct horse battery staple", ciphertext)
        self.assertEqual(crypto.decrypt(ciphertext), "correct horse battery staple")

    def test_wrong_master_key_refuses_to_decrypt(self):
        os.environ[crypto.MASTER_KEY_ENV_VAR] = "key-one"
        ciphertext = crypto.encrypt("a secret")
        os.environ[crypto.MASTER_KEY_ENV_VAR] = "key-two"
        with self.assertRaises(UserError):
            crypto.decrypt(ciphertext)

    def test_decrypt_of_falsy_value_is_falsy(self):
        os.environ[crypto.MASTER_KEY_ENV_VAR] = "a-test-master-key"
        self.assertFalse(crypto.decrypt(False))
        self.assertFalse(crypto.decrypt(None))
