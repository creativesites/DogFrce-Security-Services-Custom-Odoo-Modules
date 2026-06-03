from datetime import date, timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SecurityIncidentType(models.Model):
    _name = "security.incident.type"
    _description = "Security Incident Type"
    _order = "name"

    name = fields.Char(required=True)
    code = fields.Char()
    deduction_amount = fields.Float(default=0.0)
    reliability_score_delta = fields.Integer(default=0)
    high_trust_exclusion = fields.Boolean(default=False)
    active = fields.Boolean(default=True)
    note = fields.Text()
    # G-16: severity for progressive discipline
    severity = fields.Selection(
        [("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")],
        default="medium",
        required=True,
        string="Severity",
    )


class SecurityIncident(models.Model):
    _name = "security.incident"
    _description = "Security Incident"
    # G-13: inherit mail.thread + mail.activity.mixin
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "incident_date desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        domain=[("security_guard", "=", True)],
    )
    incident_type_id = fields.Many2one("security.incident.type", required=True)
    incident_date = fields.Date(required=True)
    approved_by_id = fields.Many2one("res.users")
    deduction_amount = fields.Float(
        compute="_compute_defaults",
        store=True,
        tracking=True,  # G-13
    )
    reliability_score_delta = fields.Integer(
        compute="_compute_defaults",
        store=True,
    )
    high_trust_exclusion = fields.Boolean(
        compute="_compute_defaults",
        store=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("approved", "Approved"),
            ("resolved", "Resolved"),
        ],
        default="draft",
        required=True,
        tracking=True,  # G-13
    )
    payslip_id = fields.Many2one("security.payslip", ondelete="set null")
    note = fields.Text()

    # G-14: acknowledgment fields
    acknowledged = fields.Boolean(default=False, string="Acknowledged by Guard/Supervisor")
    acknowledged_date = fields.Datetime(readonly=True, string="Acknowledgment Date")
    acknowledged_by_id = fields.Many2one("res.users", readonly=True, string="Acknowledged By")

    # G-15: appeal workflow fields
    appeal_state = fields.Selection(
        [
            ("none", "No Appeal"),
            ("appealed", "Appealed"),
            ("upheld", "Upheld — Original Decision Stands"),
            ("overturned", "Overturned — Incident Reversed"),
        ],
        default="none",
        string="Appeal Status",
        tracking=True,
    )
    appeal_reason = fields.Text(string="Appeal Reason")
    appeal_reviewed_by_id = fields.Many2one("res.users", readonly=True, string="Appeal Reviewer")
    appeal_review_date = fields.Datetime(readonly=True)

    @api.depends("employee_id", "incident_type_id", "incident_date")
    def _compute_name(self):
        for incident in self:
            employee = incident.employee_id.name or ""
            incident_type = incident.incident_type_id.name or ""
            date_val = incident.incident_date or ""
            incident.name = f"{employee} - {incident_type} - {date_val}".strip(" -")

    @api.depends(
        "incident_type_id.deduction_amount",
        "incident_type_id.reliability_score_delta",
        "incident_type_id.high_trust_exclusion",
    )
    def _compute_defaults(self):
        for incident in self:
            incident.deduction_amount = incident.incident_type_id.deduction_amount
            incident.reliability_score_delta = (
                incident.incident_type_id.reliability_score_delta
            )
            incident.high_trust_exclusion = (
                incident.incident_type_id.high_trust_exclusion
            )

    @api.constrains("deduction_amount")
    def _check_deduction_amount(self):
        for incident in self:
            if incident.deduction_amount < 0:
                raise ValidationError("Incident deduction amount cannot be negative.")

    def action_approve(self):
        adjustment_model = self.env["security.reliability.adjustment"]
        for incident in self:
            if incident.state == "approved":
                continue
            incident.state = "approved"
            if incident.reliability_score_delta:
                adjustment_model.create(
                    {
                        "employee_id": incident.employee_id.id,
                        "adjustment_date": incident.incident_date,
                        "score_delta": incident.reliability_score_delta,
                        "reason": incident.incident_type_id.name,
                        "note": incident.note,
                    }
                )
                incident.employee_id.security_reliability_score += (
                    incident.reliability_score_delta
                )
            # G-14: post chatter message on approval
            incident.message_post(
                body=(
                    f"Incident approved by {self.env.user.name}. "
                    f"Deduction: N$ {incident.deduction_amount:.2f}. "
                    f"Reliability delta: {incident.reliability_score_delta}."
                ),
                subtype_xmlid="mail.mt_note",
            )
            # G-14: create system notification for supervisor
            if "security.notification" in self.env:
                self.env["security.notification"].sudo().create({
                    "title": f"Incident Approved: {incident.employee_id.name}",
                    "body": (
                        f"Incident '{incident.incident_type_id.name}' for "
                        f"{incident.employee_id.name} has been approved. "
                        f"Please ensure guard acknowledgment is obtained."
                    ),
                    "notification_type": "system",
                    "severity": "warning",
                })
            # G-16: check progressive discipline after approval
            incident.employee_id._check_progressive_discipline()

    def action_resolve(self):
        for incident in self:
            incident.state = "resolved"

    def action_reset_to_draft(self):
        for incident in self:
            incident.state = "draft"

    # G-14: acknowledgment method
    def action_mark_acknowledged(self):
        for incident in self:
            incident.acknowledged = True
            incident.acknowledged_date = fields.Datetime.now()
            incident.acknowledged_by_id = self.env.user.id
            incident.message_post(
                body=(
                    f"Incident acknowledged by {self.env.user.name} on "
                    f"{fields.Datetime.now().strftime('%Y-%m-%d %H:%M')}."
                ),
                subtype_xmlid="mail.mt_note",
            )

    # G-15: appeal methods
    def action_appeal(self):
        for incident in self:
            if incident.state == "approved":
                incident.appeal_state = "appealed"
                incident.message_post(
                    body=f"Appeal submitted by {self.env.user.name}.",
                    subtype_xmlid="mail.mt_note",
                )

    def action_uphold_appeal(self):
        for incident in self:
            incident.appeal_state = "upheld"
            incident.appeal_reviewed_by_id = self.env.user.id
            incident.appeal_review_date = fields.Datetime.now()
            incident.message_post(
                body=f"Appeal upheld by {self.env.user.name} — original decision stands.",
                subtype_xmlid="mail.mt_note",
            )

    def action_overturn_appeal(self):
        for incident in self:
            incident.appeal_state = "overturned"
            incident.appeal_reviewed_by_id = self.env.user.id
            incident.appeal_review_date = fields.Datetime.now()
            # Reverse the reliability score delta
            if incident.reliability_score_delta:
                incident.employee_id.security_reliability_score -= incident.reliability_score_delta
                self.env["security.reliability.adjustment"].create({
                    "employee_id": incident.employee_id.id,
                    "adjustment_date": fields.Date.context_today(self),
                    "score_delta": -incident.reliability_score_delta,
                    "reason": f"Appeal overturned: {incident.incident_type_id.name}",
                })
            # Void the payroll deduction if linked
            if incident.payslip_id:
                linked_lines = incident.payslip_id.deduction_line_ids.filtered(
                    lambda l: l.deduction_type == "incident"
                )
                linked_lines.unlink()
            incident.state = "resolved"
            incident.message_post(
                body=(
                    f"Appeal overturned by {self.env.user.name} — "
                    f"incident reversed, reliability score restored."
                ),
                subtype_xmlid="mail.mt_note",
            )


class SecurityPayslip(models.Model):
    _inherit = "security.payslip"

    incident_ids = fields.Many2many(
        "security.incident",
        "security_payslip_incident_rel",
        "payslip_id",
        "incident_id",
        string="Behavioral Incidents",
    )


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    # G-16: progressive discipline fields
    security_suspension_recommended = fields.Boolean(
        default=False,
        readonly=True,
        string="Suspension Recommended",
    )
    security_suspension_reason = fields.Char(readonly=True)

    # G-16: one2many back-ref to incidents
    incident_ids = fields.One2many(
        "security.incident", "employee_id", string="Incidents"
    )

    def _check_progressive_discipline(self):
        """Check if guard has 3+ medium/high/critical incidents in last 90 days."""
        cutoff = date.today() - timedelta(days=90)
        for employee in self:
            recent_incidents = self.env["security.incident"].search([
                ("employee_id", "=", employee.id),
                ("state", "=", "approved"),
                ("incident_date", ">=", str(cutoff)),
                ("incident_type_id.severity", "in", ["medium", "high", "critical"]),
            ])
            if len(recent_incidents) >= 3:
                employee.security_suspension_recommended = True
                employee.security_suspension_reason = (
                    f"{len(recent_incidents)} medium/high/critical incidents in the last 90 days."
                )
            else:
                employee.security_suspension_recommended = False
                employee.security_suspension_reason = ""
