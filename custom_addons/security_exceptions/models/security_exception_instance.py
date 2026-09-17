from odoo import api, fields, models


class SecurityExceptionInstance(models.Model):
    """One triaged exception, 1:1 with an open security.notification row
    (docs/deployguard/BUILD-STATUS-AND-PHASE-PLAN.md Phase 6.1). The
    unique constraint on notification_id IS the dedupe mechanism -- a
    second sync run for the same still-open notification is a no-op, not
    a second instance."""

    _name = "security.exception.instance"
    _description = "Exception Instance"
    _inherit = ["mail.thread"]
    _order = "tier, first_seen_at desc"

    notification_id = fields.Many2one("security.notification", required=True, ondelete="cascade")
    rule_id = fields.Many2one("security.exception.rule", required=True, ondelete="restrict")
    tier = fields.Selection(related="rule_id.tier", store=True)

    title = fields.Char(related="notification_id.title", store=True, readonly=True)
    site_id = fields.Many2one(related="notification_id.site_id", store=True, readonly=True)

    state = fields.Selection(
        [
            ("open", "Open"),
            ("acknowledged", "Acknowledged"),
            ("resolved", "Resolved"),
            ("auto_resolved", "Auto-resolved"),
            ("stale_paused", "Paused (stale data)"),
        ],
        default="open", required=True, tracking=True,
    )
    first_seen_at = fields.Datetime(default=fields.Datetime.now, required=True)
    last_confirmed_at = fields.Datetime(
        default=fields.Datetime.now, required=True,
        help="Set every sync run while the source notification is still open. Drives the stale-data pause.",
    )
    escalation_level = fields.Integer(default=0, tracking=True)
    escalated_at = fields.Datetime(readonly=True)
    acknowledged_by_id = fields.Many2one("res.users", readonly=True)
    acknowledged_at = fields.Datetime(readonly=True)
    resolved_at = fields.Datetime(readonly=True)

    _notification_unique = models.Constraint(
        "unique(notification_id)",
        "An exception instance already exists for this notification -- ingest is 1:1, never duplicated.",
    )

    # -- Ingestion (6.1, 6.2) ------------------------------------------

    @api.model
    def action_sync_from_notifications(self):
        """Cron entry point. For every active rule: open an instance for
        any of its notification_type's still-open (not dismissed)
        security.notification rows that don't have one yet; refresh
        last_confirmed_at on ones that already do; and auto-resolve
        instances whose source notification has since been dismissed --
        that dismissal IS the "condition cleared" signal, since
        security_notifications' own scans re-check their own conditions
        (e.g. a roster slot search excludes dismissed notifications
        implicitly by re-creating a fresh one if the gap recurs)."""
        Notification = self.env["security.notification"]
        for rule in self.env["security.exception.rule"].search([("active", "=", True)]):
            open_notifications = Notification.search([
                ("notification_type", "=", rule.notification_type),
                ("state", "!=", "dismissed"),
            ])
            open_ids = set(open_notifications.ids)

            existing = self.search([("rule_id", "=", rule.id)])
            existing_by_notification = {inst.notification_id.id: inst for inst in existing}

            for notification in open_notifications:
                instance = existing_by_notification.get(notification.id)
                if instance:
                    if instance.state not in ("resolved", "auto_resolved"):
                        instance.last_confirmed_at = fields.Datetime.now()
                        if instance.state == "stale_paused":
                            instance.state = "open"
                    continue
                self.create({
                    "notification_id": notification.id, "rule_id": rule.id,
                })

            if rule.auto_resolve:
                to_resolve = existing.filtered(
                    lambda inst: inst.notification_id.id not in open_ids
                    and inst.state not in ("resolved", "auto_resolved")
                )
                for instance in to_resolve:
                    instance.write({"state": "auto_resolved", "resolved_at": fields.Datetime.now()})
                    instance.message_post(body="Auto-resolved: source notification is no longer open.")

    # -- Triage actions ---------------------------------------------------

    def action_acknowledge(self):
        """Acknowledging cancels escalation (spec's exit criterion)."""
        for instance in self:
            instance.write({
                "state": "acknowledged", "acknowledged_by_id": self.env.user.id,
                "acknowledged_at": fields.Datetime.now(),
            })

    def action_resolve(self):
        for instance in self:
            instance.write({"state": "resolved", "resolved_at": fields.Datetime.now()})

    def action_reopen(self):
        for instance in self:
            instance.write({
                "state": "open", "resolved_at": False, "acknowledged_at": False,
                "acknowledged_by_id": False,
            })

    # -- Escalation (6.3) -------------------------------------------------

    @api.model
    def action_process_escalations(self):
        """Cron entry point. Skips acknowledged/resolved instances
        entirely (acknowledging cancels escalation). Pauses on stale data
        before ever computing elapsed time, so a rule whose sync hasn't
        run recently never escalates on data nobody has re-checked."""
        candidates = self.search([("state", "in", ("open", "stale_paused"))])
        now = fields.Datetime.now()
        for instance in candidates:
            rule = instance.rule_id
            stale_cutoff = fields.Datetime.subtract(now, minutes=rule.stale_after_minutes)
            if instance.last_confirmed_at < stale_cutoff:
                if instance.state != "stale_paused":
                    instance.state = "stale_paused"
                continue
            if instance.state == "stale_paused":
                instance.state = "open"

            policy = rule.escalation_policy_id
            elapsed = policy._elapsed_minutes(instance.first_seen_at, now)

            if instance.escalation_level == 0 and elapsed >= policy.level1_delay_minutes:
                instance._escalate(1, policy.level1_group_id)
            elif instance.escalation_level == 1 and elapsed >= policy.level2_delay_minutes:
                instance._escalate(2, policy.level2_group_id)

    def _escalate(self, level, group):
        self.ensure_one()
        self.write({"escalation_level": level, "escalated_at": fields.Datetime.now()})
        recipients = self.env["res.users"].search([("group_ids", "in", group.id)])
        self.message_post(
            body=f"Escalated to level {level} ({group.name}): {self.title}"
        )
        if recipients:
            self.env["security.notification"].sudo().create({
                "title": f"[Escalated L{level}] {self.title}",
                "body": f"This exception has not been acknowledged and was escalated to {group.name}.",
                "notification_type": "system",
                "severity": "critical",
                "recipient_ids": [(6, 0, recipients.ids)],
                "related_model": "security.exception.instance",
                "related_id": self.id,
            })
