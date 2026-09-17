import base64
import secrets
import uuid

from odoo import api, fields, models
from odoo.exceptions import UserError

from . import security_deployguard_crypto as crypto

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
    )
    from cryptography.hazmat.primitives import serialization
    _HAS_ED25519 = True
except ImportError:  # pragma: no cover - see security_deployguard_crypto.py
    _HAS_ED25519 = False


class SecurityDeployguardConfig(models.Model):
    """Bridge configuration singleton.

    docs/deployguard/adr/DG-ADR-018-odoo-bridge-addons.md §6 and
    docs/deployguard/12-odoo-integration.md §2. One row per database
    (enforced by get_config(), not a DB constraint -- a stray second row is
    a data problem an admin can fix, not something that should crash the
    ORM).

    What this model does NOT do, on purpose: it does not implement the
    auth/SSO endpoints (DG-ADR-007). It generates and stores the signing
    keypair those endpoints will need, because key generation and
    encrypted-at-rest storage are exactly the same problem whether or not
    the endpoints exist yet, and getting it right once here means T-9 only
    has to *read* a key, not also solve this. See this module's manifest
    description for the fuller rationale.
    """

    _name = "security.deployguard.config"
    _description = "DeployGuard Bridge Configuration"
    _inherit = ["mail.thread"]

    name = fields.Char(default="DeployGuard Bridge Configuration", required=True)
    active = fields.Boolean(default=True)

    platform_base_url = fields.Char(
        string="DeployGuard Platform URL",
        help="e.g. https://platform.deployguard.example -- left empty until "
             "the Platform exists to point at (see BUILD-STATUS-AND-PHASE-"
             "PLAN.md). Nothing in this module calls out to this URL yet.",
    )
    tenant_id = fields.Char(
        string="Tenant ID",
        help="The tenant identifier the Platform assigns this database. "
             "Set once the Platform allocates one.",
    )
    contract_version = fields.Char(default="v1", required=True, tracking=True)

    integration_user_id = fields.Many2one(
        "res.users", string="Integration User", readonly=True,
        help="Created automatically on install. Generate its API key under "
             "that user's My Profile > Account Security, then hand the key "
             "to the Platform's Odoo integration setup -- this module does "
             "not generate or store that key itself; it is a standard Odoo "
             "user API key (res.users.apikeys).",
    )

    # -- Webhook secret (HMAC key the outbox signs deliveries with) --------
    # Never exposed in plaintext once set. webhook_secret_set is what every
    # view shows; the raw value is only ever returned once, by
    # action_generate_webhook_secret's result, and never logged.
    webhook_secret_encrypted = fields.Char(string="Webhook Secret (encrypted)", copy=False)
    webhook_secret_set = fields.Boolean(compute="_compute_webhook_secret_set")
    webhook_secret_rotated_at = fields.Datetime(readonly=True)

    # -- Bridge signing keypair (Ed25519, for future JWS assertions) -------
    signing_private_key_encrypted = fields.Char(
        string="Signing Private Key (encrypted)", copy=False
    )
    signing_public_key = fields.Char(
        string="Signing Public Key",
        readonly=True,
        help="Safe to share -- hand this to the Platform's Odoo integration "
             "setup together with the Key ID below.",
    )
    signing_key_id = fields.Char(
        string="Key ID (kid)", readonly=True,
        help="Rotation identifier. A new keypair gets a new kid; the "
             "Platform can accept both during a rotation window.",
    )
    signing_key_rotated_at = fields.Datetime(readonly=True)

    master_key_configured = fields.Boolean(
        compute="_compute_master_key_configured",
        string="Master Key Configured",
        help="Whether DEPLOYGUARD_MASTER_KEY (or odoo.conf's "
             "deployguard_master_key) is set. Secrets cannot be generated "
             "until this is true.",
    )

    def _compute_webhook_secret_set(self):
        for rec in self:
            rec.webhook_secret_set = bool(rec.webhook_secret_encrypted)

    def _compute_master_key_configured(self):
        configured = crypto.master_key_configured()
        for rec in self:
            rec.master_key_configured = configured

    @api.model
    def get_config(self):
        """The one config row, creating it if truly missing (e.g. a
        database that installed this module before post_init_hook existed,
        or restored from a backup taken before it ran)."""
        config = self.sudo().search([], limit=1)
        if not config:
            config = self.sudo().create({"name": "DeployGuard Bridge Configuration"})
        return config

    # -- Webhook secret lifecycle -------------------------------------------

    def action_generate_webhook_secret(self):
        """Generates a new webhook secret, stores it encrypted, and shows
        the plaintext value exactly once via a notification. There is no
        way to retrieve it again afterwards -- regenerate instead."""
        self.ensure_one()
        secret = secrets.token_urlsafe(32)
        self.write({
            "webhook_secret_encrypted": crypto.encrypt(secret),
            "webhook_secret_rotated_at": fields.Datetime.now(),
        })
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Webhook secret generated",
                "message": (
                    f"Copy this now -- it will not be shown again: {secret}"
                ),
                "sticky": True,
                "type": "success",
            },
        }

    def get_webhook_secret(self):
        """For the outbox dispatcher only. Never call this from a view or
        expose its result to a controller response."""
        self.ensure_one()
        if not self.webhook_secret_encrypted:
            raise UserError(
                "No webhook secret configured yet. Generate one on the "
                "DeployGuard Bridge configuration page first."
            )
        return crypto.decrypt(self.webhook_secret_encrypted)

    # -- Signing keypair lifecycle -------------------------------------------

    def action_generate_signing_keypair(self):
        """Generates a new Ed25519 keypair for this tenant. The private key
        is stored encrypted; the public key and a new kid are stored in the
        clear for handing to the Platform.

        No auth endpoint reads this yet (see the module docstring) -- this
        button exists so the operational step ("generate and hand over the
        bridge's public key", 12-odoo-integration.md §2 step 4) can happen
        independently of when the auth endpoints ship.
        """
        self.ensure_one()
        if not _HAS_ED25519:
            raise UserError(
                "The 'cryptography' package's Ed25519 support is not "
                "available in this Odoo installation."
            )
        private_key = Ed25519PrivateKey.generate()
        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.write({
            "signing_private_key_encrypted": crypto.encrypt(
                base64.urlsafe_b64encode(private_bytes).decode("ascii")
            ),
            "signing_public_key": base64.urlsafe_b64encode(public_bytes).decode("ascii"),
            "signing_key_id": uuid.uuid4().hex[:12],
            "signing_key_rotated_at": fields.Datetime.now(),
        })
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Signing keypair generated",
                "message": (
                    f"Key ID {self.signing_key_id} -- hand the public key "
                    "and this Key ID to the DeployGuard Platform's Odoo "
                    "integration settings."
                ),
                "sticky": True,
                "type": "success",
            },
        }

    def get_signing_private_key(self):
        """For future auth-endpoint code only (DG-ADR-007). Not called by
        anything in this slice."""
        self.ensure_one()
        if not self.signing_private_key_encrypted:
            raise UserError(
                "No signing keypair configured yet. Generate one on the "
                "DeployGuard Bridge configuration page first."
            )
        return base64.urlsafe_b64decode(
            crypto.decrypt(self.signing_private_key_encrypted).encode("ascii")
        )
