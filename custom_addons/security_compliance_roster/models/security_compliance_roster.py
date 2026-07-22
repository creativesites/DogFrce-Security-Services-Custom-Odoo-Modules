import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SecurityRosterSlot(models.Model):
    _inherit = "security.roster.slot"

    compliance_override = fields.Boolean(
        default=False,
        string="Emergency Compliance Override",
        help="Check to bypass certification, licensing, attributes, and language matching constraints under authorized emergencies.",
    )
    compliance_override_reason = fields.Char(
        string="Override Justification",
        help="Specify the technical or operational emergency reason for bypassing compliance constraints.",
    )
    compliance_override_user_id = fields.Many2one(
        "res.users",
        string="Authorized Override User",
        default=lambda self: self.env.user,
        help="The system user who authorized the bypass of compliance matching rules.",
    )

    @api.constrains("employee_id", "post_id", "shift_requirement_id")
    def _check_guard_eligibility(self):
        """
        Extends roster eligibility constraints. If compliance override is checked and justified,
        it registers an unalterable audit-trail log inside the event bus and skips the constraints block.
        """
        overridden_slots = self.filtered(lambda s: s.compliance_override)
        standard_slots = self - overridden_slots

        # 1. Standard slots undergo default Odoo eligibility constraints
        if standard_slots:
            super(SecurityRosterSlot, standard_slots)._check_guard_eligibility()

        # 2. Process overridden slots: enforce mandatory justification and register security audit trail
        for slot in overridden_slots:
            if not slot.compliance_override_reason:
                raise ValidationError(_(
                    "Compliance Override requested for Guard '%s' on Shift Date '%s' at Post '%s' "
                    "but no Override Justification was specified! Bypassing compliance requires a justification."
                ) % (slot.employee_id.name or "", slot.shift_date, slot.post_id.name or ""))

            # Register a permanent compliance audit-trail log on the Central Intelligence Bus
            payload = {
                "roster_slot": slot.name,
                "guard": slot.employee_id.name,
                "site": slot.site_id.name if slot.site_id else _("Unknown Site"),
                "post": slot.post_id.name if slot.post_id else _("Unknown Post"),
                "shift_date": str(slot.shift_date),
                "authorized_by": slot.compliance_override_user_id.name or slot.env.user.name,
                "justification": slot.compliance_override_reason,
            }

            self.env["security.event.log"].register_event(
                name="compliance.bypass",
                source_model="security.roster.slot",
                source_id=slot.id,
                payload=payload,
            )


class SecurityEmployeeDocument(models.Model):
    _inherit = "security.employee.document"

    @api.model
    def action_cron_expiry_warnings(self):
        """
        Extends the standard daily cron run to forward expiring document warnings
        directly to the DeployGuard central intelligence bus.
        """
        super(SecurityEmployeeDocument, self).action_cron_expiry_warnings()

        today = fields.Date.context_today(self)
        from datetime import timedelta
        warning_days = [7, 14, 30]

        for days in warning_days:
            target_date = today + timedelta(days=days)
            expiring = self.search([
                ("expiry_date", "=", target_date),
                ("state", "not in", ("expired", "rejected")),
            ])

            if not expiring:
                continue

            for doc in expiring:
                if not doc.employee_id:
                    continue

                payload = {
                    "employee": doc.employee_id.name,
                    "document_type": doc.document_type_id.name,
                    "document_number": doc.document_number or "N/A",
                    "expiry_date": str(doc.expiry_date),
                    "days_remaining": days,
                }

                self.env["security.event.log"].register_event(
                    name="compliance.expiring_documents",
                    source_model="security.employee.document",
                    source_id=doc.id,
                    payload=payload,
                )


class SecurityComplianceRosterBridge(models.AbstractModel):
    _name = "security.compliance.roster.bridge"
    _description = "Security Compliance and Roster Intelligence Bridge"

    @api.model
    def _handle_bus_event(self, event_name, source_model, source_id, payload):
        """
        Listens to compliance events and raises critical operational alerts inside Odoo.
        """
        _logger.info("Compliance Bridge | Processing event: %s", event_name)

        if event_name == "compliance.bypass":
            guard = payload.get("guard", "")
            post = payload.get("post", "")
            site = payload.get("site", "")
            auth_by = payload.get("authorized_by", "")
            justification = payload.get("justification", "")

            _logger.warning("Compliance Bridge | EMERGENCY COMPLIANCE OVERRIDE! Guard: %s, Authorized by: %s", guard, auth_by)

            audit_msg = _(
                "EMERGENCY COMPLIANCE OVERRIDE RECORDED:\n"
                "Guard '%s' was deployed to Post '%s' at Site '%s' bypassing compliance checks.\n\n"
                "Authorized By: %s\n"
                "Justification: %s"
            ) % (guard, post, site, auth_by, justification)

            # Insert an unalterable HIGH-priority log entry
            self.env["security.event.log"].create({
                "name": f"COMPLIANCE OVERRIDE: {guard}",
                "event_type": "compliance_override",
                "severity": "high",
                "description": audit_msg,
            })

        elif event_name == "compliance.expiring_documents":
            employee = payload.get("employee", "")
            doc_type = payload.get("document_type", "")
            days = payload.get("days_remaining", 0)
            exp_date = payload.get("expiry_date", "")

            _logger.warning("Compliance Bridge | Expiring License Warning: Employee %s, Document %s, Expiry: %s", employee, doc_type, exp_date)

            alert_msg = _(
                "LICENSE EXPIRATION ALERT (%s Days):\n"
                "The licensing/credential document '%s' for Guard '%s' is expiring on: %s.\n\n"
                "Guards with expired licenses will be automatically blocked from roster deployments."
            ) % (days, doc_type, employee, exp_date)

            self.env["security.event.log"].create({
                "name": f"EXPIRING DOCUMENT: {employee} ({doc_type})",
                "event_type": "compliance_expiration",
                "severity": "medium",
                "description": alert_msg,
            })
