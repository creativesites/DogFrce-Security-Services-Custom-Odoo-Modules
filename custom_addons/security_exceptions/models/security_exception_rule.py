from odoo import fields, models

# Mirrors security.notification's notification_type selection, minus
# "system" and "sms_alert" -- those are generic/delivery channels, not
# operational exceptions with a tier and an escalation path.
NOTIFICATION_TYPES = [
    ("document_expiry", "Document Expiry"),
    ("cert_expiry", "Certification Expiry"),
    ("invoice_overdue", "Invoice Overdue"),
    ("awol_alert", "AWOL Alert"),
    ("roster_gap", "Roster Gap"),
    ("override_audit", "Ineligibility Override Audit"),
]

TIERS = [
    ("critical", "Critical"),
    ("attention", "Attention"),
    ("watch", "Watch"),
]


class SecurityExceptionRule(models.Model):
    """Tenant configuration mapping one security.notification
    notification_type to a triage tier and escalation policy
    (docs/deployguard/BUILD-STATUS-AND-PHASE-PLAN.md Phase 6.1, 6.2).
    Deliberately does not duplicate any detection logic -- the source of
    truth for "is there a roster gap" stays security_notifications'
    action_scan_roster_gaps and friends; this rule only decides how
    seriously to treat an alert that already exists."""

    _name = "security.exception.rule"
    _description = "Exception Rule"
    _order = "tier, notification_type"

    notification_type = fields.Selection(NOTIFICATION_TYPES, required=True)
    name = fields.Char(compute="_compute_name", store=True)
    tier = fields.Selection(TIERS, required=True)
    escalation_policy_id = fields.Many2one("security.exception.escalation.policy", required=True)
    auto_resolve = fields.Boolean(
        default=True,
        help="Auto-resolve the exception instance the moment its source notification is dismissed.",
    )
    stale_after_minutes = fields.Integer(
        default=60,
        help="If the sync cron hasn't reconfirmed this instance's source notification is still open within this many minutes, escalation pauses (stale_paused) rather than escalating on unrefreshed data.",
    )
    active = fields.Boolean(default=True)

    _notification_type_unique = models.Constraint(
        "unique(notification_type)",
        "Only one Exception Rule per notification_type.",
    )

    def _compute_name(self):
        labels = dict(NOTIFICATION_TYPES)
        for rule in self:
            rule.name = labels.get(rule.notification_type, rule.notification_type)
