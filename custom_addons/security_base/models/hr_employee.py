from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    security_guard = fields.Boolean(default=False, tracking=True)
    security_grade_id = fields.Many2one("security.grade", tracking=True)
    security_hourly_rate = fields.Float(
        default=0.0,
        help="Optional employee-specific hourly rate. If blank, payroll uses the guard grade rate.",
    )
    security_certification_ids = fields.Many2many(
        "security.certification",
        "hr_employee_security_certification_rel",
        "employee_id",
        "certification_id",
        string="Certifications",
    )
    security_language_ids = fields.Many2many(
        "security.language",
        "hr_employee_security_language_rel",
        "employee_id",
        "language_id",
        string="Language Skills",
    )
    security_attribute_ids = fields.Many2many(
        "security.attribute",
        "hr_employee_security_attribute_rel",
        "employee_id",
        "attribute_id",
        string="Attributes",
    )
    security_reliability_score = fields.Integer(default=100, tracking=True)
    security_home_location = fields.Char()
    security_medical_fitness_grade = fields.Char()
    security_disqualified = fields.Boolean(default=False, tracking=True)
    security_disqualification_reason_id = fields.Many2one(
        "security.disqualification.reason",
        tracking=True,
    )
    security_disqualification_note = fields.Text()
    security_reliability_adjustment_ids = fields.One2many(
        "security.reliability.adjustment",
        "employee_id",
        string="Reliability Adjustments",
    )
    security_reliability_adjustment_total = fields.Integer(
        compute="_compute_security_reliability_adjustment_total"
    )
    security_effective_hourly_rate = fields.Float(
        compute="_compute_security_effective_hourly_rate",
    )

    # Mobile app fields
    security_mobile_pin_hash = fields.Char(
        string="Mobile PIN (Hashed)",
        copy=False,
        groups="security_base.group_security_manager",
        help="Bcrypt-hashed 4-digit PIN for quick mobile re-authentication.",
    )
    security_mobile_device_token = fields.Char(
        string="FCM Device Token",
        copy=False,
        help="Firebase Cloud Messaging token for push notifications.",
    )
    security_mobile_last_login = fields.Datetime(
        string="Last Mobile Login",
        readonly=True,
        copy=False,
    )

    @api.depends("security_reliability_adjustment_ids.score_delta")
    def _compute_security_reliability_adjustment_total(self):
        for employee in self:
            employee.security_reliability_adjustment_total = sum(
                employee.security_reliability_adjustment_ids.mapped("score_delta")
            )

    @api.depends("security_hourly_rate", "security_grade_id.hourly_rate")
    def _compute_security_effective_hourly_rate(self):
        for employee in self:
            employee.security_effective_hourly_rate = (
                employee.security_hourly_rate or employee.security_grade_id.hourly_rate
            )
