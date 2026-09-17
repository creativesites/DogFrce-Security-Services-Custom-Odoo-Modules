import hashlib
import hmac
import json
import logging
import uuid

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# 1 minute -> 2 -> 4 -> ... capped at 24 hours, then dead. Mirrors
# security_reconciliation_core's job retry shape for operator familiarity
# (DG-ADR-018 §3).
BASE_RETRY_MINUTES = 1
MAX_RETRY_MINUTES = 24 * 60
MAX_ATTEMPTS = 20  # generous; the cap on delay makes this take days to exhaust
BATCH_SIZE = 200  # DG-ADR-018 §3: batches of <= 200


class SecurityDeployguardOutbox(models.Model):
    """Outbound event queue to the DeployGuard Platform.

    docs/deployguard/adr/DG-ADR-018-odoo-bridge-addons.md §3. Rows are
    written by domain bridges inside the same transaction as the change
    they describe (none exist yet in this slice -- see the manifest). This
    model and its dispatch cron exist now so that when the first domain
    bridge (attendance, per DG-ADR-018's table) is built, it only has to
    call `SecurityDeployguardOutbox.enqueue(...)`, not design a delivery
    mechanism.

    There is deliberately no HTTP call anywhere in this file yet: the
    Platform endpoint this would POST to
    (`/v1/integrations/odoo/webhooks`) does not exist (BUILD-STATUS-AND-
    PHASE-PLAN.md P0/P1 status). `_dispatch_one` signs and logs what it
    would have sent and marks the row `failed` with a clear error, so the
    retry/backoff/dead-lettering machinery is real and testable today, and
    becomes "send it for real" as a single, small, later change once
    there's a URL to send it to.
    """

    _name = "security.deployguard.outbox"
    _description = "DeployGuard Outbox"
    _order = "next_attempt_at, id"

    event_id = fields.Char(
        default=lambda self: str(uuid.uuid4()), required=True, readonly=True, index=True
    )
    event_type = fields.Char(required=True, index=True)
    event_version = fields.Integer(default=1, required=True)
    occurred_at = fields.Datetime(default=fields.Datetime.now, required=True)
    model = fields.Char(help="The Odoo model this event describes, e.g. security.attendance.batch")
    res_id = fields.Integer()
    payload = fields.Text(
        required=True,
        help="JSON-serialised event body, matching the envelope in "
             "docs/deployguard/12-odoo-integration.md §4.",
    )
    correlation_id = fields.Char(index=True)

    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("sent", "Sent"),
            ("failed", "Failed"),
            ("dead", "Dead"),
        ],
        default="pending",
        required=True,
        index=True,
    )
    attempts = fields.Integer(default=0)
    next_attempt_at = fields.Datetime(default=fields.Datetime.now, index=True)
    last_error = fields.Char()
    sent_at = fields.Datetime(readonly=True)

    _sql_constraints = [
        ("unique_event_id", "unique(event_id)", "An outbox event_id must be unique."),
    ]

    @api.model
    def enqueue(self, event_type, data, model=False, res_id=False, correlation_id=False):
        """The one entry point domain bridges call. Builds the envelope
        described in 12-odoo-integration.md §4 and writes it in the caller's
        own transaction -- callers should call this from inside the same
        `create`/`write`/state-transition method the event describes, not
        from a separate cron or a post-commit hook, so the event can never
        be lost to a rollback that also undoes the change it describes.
        """
        config = self.env["security.deployguard.config"].get_config()
        event_id = str(uuid.uuid4())
        envelope = {
            "event_id": event_id,
            "type": event_type,
            "version": 1,
            "occurred_at": fields.Datetime.to_string(fields.Datetime.now()),
            "odoo": {
                "model": model,
                "res_id": res_id,
                "write_date": fields.Datetime.to_string(fields.Datetime.now()),
            },
            "data": data,
            "correlation_id": correlation_id or str(uuid.uuid4()),
        }
        return self.create({
            "event_id": event_id,
            "event_type": event_type,
            "model": model,
            "res_id": res_id,
            "payload": json.dumps(envelope),
            "correlation_id": envelope["correlation_id"],
        })

    def _sign(self, secret: str) -> str:
        """HMAC-SHA256 over the raw payload, in the `t=...,v1=...` form
        DG-ADR-018 §3 / 12-odoo-integration.md §4 describe."""
        self.ensure_one()
        timestamp = str(int(fields.Datetime.now().timestamp()))
        signed_content = f"{timestamp}.{self.payload}".encode("utf-8")
        digest = hmac.new(secret.encode("utf-8"), signed_content, hashlib.sha256).hexdigest()
        return f"t={timestamp},v1={digest}"

    @api.model
    def action_dispatch_due(self, limit=BATCH_SIZE):
        """Cron entry point. Picks up due rows and attempts delivery.

        Batches by nothing more than "oldest due first, up to BATCH_SIZE" --
        DG-ADR-018 says batches of <= 200 events are sent per delivery, which
        this satisfies without needing to group rows into a single HTTP call
        yet (there is no endpoint to call).
        """
        now = fields.Datetime.now()
        rows = self.search(
            [("state", "in", ("pending", "failed")), ("next_attempt_at", "<=", now)],
            limit=limit,
            order="next_attempt_at, id",
        )
        for row in rows:
            row._dispatch_one()

    def _dispatch_one(self):
        self.ensure_one()
        config = self.env["security.deployguard.config"].get_config()

        if not config.platform_base_url:
            # Expected and normal until the Platform exists -- log once per
            # attempt at debug level, not warning, so this isn't noise in
            # every install's logs before P0/P1 ship.
            _logger.debug(
                "DeployGuard outbox event %s not dispatched: no Platform "
                "URL configured yet.", self.event_id,
            )
            self._reschedule("No DeployGuard Platform URL configured yet.")
            return

        try:
            secret = config.get_webhook_secret()
        except Exception as exc:  # noqa: BLE001 - surfaced as a clear retry reason
            self._reschedule(str(exc))
            return

        signature = self._sign(secret)

        # No HTTP call yet -- see this file's class docstring. Once
        # /v1/integrations/odoo/webhooks exists, this branch becomes a real
        # `requests.post(...)` with X-DG-Signature: signature, and success
        # marks the row sent instead of always retrying.
        _logger.info(
            "DeployGuard outbox event %s (%s) signed and ready to send to %s "
            "-- delivery not yet implemented, no Platform endpoint exists.",
            self.event_id, self.event_type, config.platform_base_url,
        )
        self._reschedule(
            "Delivery not implemented yet: no live Platform endpoint "
            "(BUILD-STATUS-AND-PHASE-PLAN.md P0/P1). Signed successfully; "
            "queued for when it does."
        )

    def _reschedule(self, error):
        self.ensure_one()
        attempts = self.attempts + 1
        if attempts >= MAX_ATTEMPTS:
            self.write({"state": "dead", "attempts": attempts, "last_error": error})
            return
        delay_minutes = min(BASE_RETRY_MINUTES * (2 ** (attempts - 1)), MAX_RETRY_MINUTES)
        self.write({
            "state": "failed",
            "attempts": attempts,
            "last_error": error,
            "next_attempt_at": fields.Datetime.add(fields.Datetime.now(), minutes=delay_minutes),
        })

    def action_requeue(self):
        """Manual retry from the outbox monitor -- resets attempts so a row
        that went dead because of a fixable problem (e.g. the master key
        was missing) gets the full backoff schedule again."""
        self.filtered(lambda r: r.state in ("failed", "dead")).write({
            "state": "pending",
            "attempts": 0,
            "next_attempt_at": fields.Datetime.now(),
            "last_error": False,
        })
