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


class SecurityIncident(models.Model):
    _name = "security.incident"
    _description = "Security Incident"
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
    )
    payslip_id = fields.Many2one("security.payslip", ondelete="set null")
    note = fields.Text()

    @api.depends("employee_id", "incident_type_id", "incident_date")
    def _compute_name(self):
        for incident in self:
            employee = incident.employee_id.name or ""
            incident_type = incident.incident_type_id.name or ""
            date = incident.incident_date or ""
            incident.name = f"{employee} - {incident_type} - {date}".strip(" -")

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

    def action_resolve(self):
        for incident in self:
            incident.state = "resolved"

    def action_reset_to_draft(self):
        for incident in self:
            incident.state = "draft"


class SecurityPayslip(models.Model):
    _inherit = "security.payslip"

    incident_ids = fields.Many2many(
        "security.incident",
        "security_payslip_incident_rel",
        "payslip_id",
        "incident_id",
        string="Behavioral Incidents",
    )
