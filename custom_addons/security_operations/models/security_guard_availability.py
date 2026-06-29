from odoo import fields, models


class SecurityGuardAvailability(models.Model):
    _name = "security.guard.availability"
    _description = "Guard Availability Preferences"
    _order = "employee_id"

    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        ondelete="cascade",
        string="Guard",
        domain=[("security_guard", "=", True)],
    )
    preferred_shift_template_ids = fields.Many2many(
        "security.shift.template",
        string="Preferred Shifts",
    )
    max_shifts_per_week = fields.Integer(
        default=5,
        string="Max Shifts / Week",
    )
    preferred_site_ids = fields.Many2many(
        "security.client.site",
        string="Preferred Sites",
    )
    note = fields.Text("Notes")
