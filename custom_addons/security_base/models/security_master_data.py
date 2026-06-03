from datetime import date

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SecurityGrade(models.Model):
    _name = "security.grade"
    _description = "Security Guard Grade"
    _order = "sequence, name"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    hourly_rate = fields.Float(default=0.0)
    responsibility_level = fields.Selection(
        [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("critical", "Critical"),
        ],
        default="medium",
        required=True,
    )
    note = fields.Text()


class SecurityCertification(models.Model):
    _name = "security.certification"
    _description = "Security Certification"
    _order = "name"

    name = fields.Char(required=True)
    code = fields.Char()
    active = fields.Boolean(default=True)
    expiry_required = fields.Boolean(default=False)
    note = fields.Text()


class SecurityLanguage(models.Model):
    _name = "security.language"
    _description = "Security Language Skill"
    _order = "name"

    name = fields.Char(required=True)
    code = fields.Char()
    active = fields.Boolean(default=True)


class SecurityAttribute(models.Model):
    _name = "security.attribute"
    _description = "Security Guard Attribute"
    _order = "category, name"

    name = fields.Char(required=True)
    category = fields.Selection(
        [
            ("physical", "Physical"),
            ("medical", "Medical"),
            ("training", "Training"),
            ("other", "Other"),
        ],
        default="other",
        required=True,
    )
    active = fields.Boolean(default=True)
    note = fields.Text()


class SecurityDisqualificationReason(models.Model):
    _name = "security.disqualification.reason"
    _description = "Security Disqualification Reason"
    _order = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    note = fields.Text()


class SecurityReliabilityAdjustment(models.Model):
    _name = "security.reliability.adjustment"
    _description = "Security Reliability Adjustment"
    _order = "adjustment_date desc, id desc"

    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        ondelete="cascade",
    )
    adjustment_date = fields.Date(required=True, default=fields.Date.context_today)
    score_delta = fields.Integer(required=True)
    reason = fields.Char(required=True)
    note = fields.Text()


class SecurityEmployeeCertification(models.Model):
    _name = "security.employee.certification"
    _description = "Guard Certification Record"
    _order = "expiry_date, id"

    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        ondelete="cascade",
    )
    certification_id = fields.Many2one(
        "security.certification",
        required=True,
        string="Certification Type",
    )
    issue_date = fields.Date(string="Issue Date")
    expiry_date = fields.Date(string="Expiry Date")
    verified = fields.Boolean(default=False, string="Verified")
    document_ref = fields.Char(string="Certificate Reference / Number")
    note = fields.Text()
    is_expired = fields.Boolean(
        compute="_compute_is_expired",
        store=True,
        string="Expired",
    )
    days_until_expiry = fields.Integer(
        compute="_compute_is_expired",
        store=False,
        string="Days Until Expiry",
    )

    @api.depends("expiry_date")
    def _compute_is_expired(self):
        today = date.today()
        for cert in self:
            if cert.expiry_date:
                delta = (cert.expiry_date - today).days
                cert.days_until_expiry = delta
                cert.is_expired = delta < 0
            else:
                cert.days_until_expiry = 9999
                cert.is_expired = False

    @api.constrains("issue_date", "expiry_date")
    def _check_dates(self):
        for cert in self:
            if (
                cert.issue_date
                and cert.expiry_date
                and cert.expiry_date < cert.issue_date
            ):
                raise ValidationError("Expiry date cannot be before issue date.")
