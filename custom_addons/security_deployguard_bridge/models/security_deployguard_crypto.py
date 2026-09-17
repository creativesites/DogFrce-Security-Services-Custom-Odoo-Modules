"""Encryption-at-rest for this module's secrets.

DG-ADR-018 §6: "Secrets are stored encrypted using a key from the Odoo
server configuration or environment, not in plain ir.config_parameter."
The master key never lives in the database -- an attacker with only a
database dump (backup, replica, SQL injection) must not be able to decrypt
the webhook secret or the bridge's private signing key.

The master key comes from, in order:
1. the DEPLOYGUARD_MASTER_KEY environment variable;
2. the `deployguard_master_key` key in Odoo's own config file (odoo.conf),
   read via `odoo.tools.config` -- the same place `admin_passwd` lives, so
   an operator who already manages that file has one place to look.

If neither is set, encryption is refused rather than silently falling back
to plaintext or to a key generated (and then persisted) in the database,
which would defeat the point. Everywhere in this module, "cannot encrypt" is
handled as a clear, actionable UserError -- never a silent write of an
unencrypted secret.
"""

import base64
import hashlib
import os

from odoo import tools
from odoo.exceptions import UserError

try:
    from cryptography.fernet import Fernet, InvalidToken
    _HAS_CRYPTO = True
except ImportError:  # pragma: no cover - exercised only if the dependency
    # is genuinely missing, which is not expected on the standard Odoo 19
    # Docker image (cryptography is a transitive dependency of Odoo's own
    # EDI/digital-signature features used across many localizations).
    _HAS_CRYPTO = False
    InvalidToken = Exception


MASTER_KEY_ENV_VAR = "DEPLOYGUARD_MASTER_KEY"
MASTER_KEY_CONFIG_OPTION = "deployguard_master_key"


class MissingMasterKey(UserError):
    pass


def _raw_master_key():
    value = os.environ.get(MASTER_KEY_ENV_VAR)
    if not value:
        value = tools.config.get(MASTER_KEY_CONFIG_OPTION)
    return value


def _fernet():
    if not _HAS_CRYPTO:
        raise UserError(
            "The 'cryptography' Python package is not available in this "
            "Odoo installation. DeployGuard secrets cannot be stored until "
            "it is installed -- this is expected to already be present on "
            "the standard Odoo 19 image; if it genuinely is not, add it "
            "before using this module."
        )
    raw = _raw_master_key()
    if not raw:
        raise MissingMasterKey(
            f"No DeployGuard master key configured. Set the "
            f"{MASTER_KEY_ENV_VAR} environment variable (or "
            f"'{MASTER_KEY_CONFIG_OPTION}' in odoo.conf) to a long random "
            f"value before configuring the DeployGuard Bridge. This key "
            f"encrypts the webhook secret and the bridge's private signing "
            f"key at rest -- it must never be stored in this database."
        )
    # Fernet requires a 32-byte urlsafe-base64 key. Derive one deterministically
    # from whatever the operator supplied, so the master key itself can be an
    # ordinary passphrase rather than a pre-formatted Fernet key.
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(plaintext: str) -> str:
    """Returns an opaque encrypted string, safe to store in the database."""
    if plaintext is None:
        return False
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt(ciphertext: str) -> str:
    """Reverses encrypt(). Raises UserError if the master key has changed
    or the stored value is corrupt -- never returns a wrong-but-plausible
    value."""
    if not ciphertext:
        return False
    try:
        return _fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken:
        raise UserError(
            "Could not decrypt this DeployGuard secret. Either the master "
            f"key ({MASTER_KEY_ENV_VAR}) has changed since it was stored, "
            "or the stored value is corrupt. Regenerate the secret."
        )


def master_key_configured() -> bool:
    return bool(_raw_master_key())
