from odoo import api, fields, models


class SecurityPayrollRuleSet(models.Model):
    _name = "security.payroll.rule.set"
    _description = "Security Payroll Rule Set"
    _order = "country_code, effective_from desc, id desc"

    name = fields.Char(required=True)
    country_code = fields.Char(required=True, default="NA")
    currency_id = fields.Many2one("res.currency", required=True)
    effective_from = fields.Date(required=True)
    effective_to = fields.Date()
    active = fields.Boolean(default=True)

    employee_ssc_rate = fields.Float(
        string="Employee SSC Rate",
        digits=(16, 4),
        default=0.009,
    )
    employer_ssc_rate = fields.Float(
        string="Employer SSC Rate",
        digits=(16, 4),
        default=0.009,
    )
    ssc_salary_cap = fields.Float(default=7100.0)

    sunday_multiplier = fields.Float(default=1.5)
    public_holiday_multiplier = fields.Float(default=1.5)
    saturday_multiplier = fields.Float(default=1.25)
    night_shift_multiplier = fields.Float(default=1.25)
    overtime_multiplier = fields.Float(default=1.5)

    standard_shift_hours = fields.Float(default=12.0)
    vat_rate = fields.Float(default=15.0)
    legal_invoice_text = fields.Text()


class SecurityTaxBracket(models.Model):
    _name = "security.tax.bracket"
    _description = "Security Tax Bracket"
    _order = "rule_set_id, lower_bound"

    rule_set_id = fields.Many2one(
        "security.payroll.rule.set",
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(compute="_compute_name", store=True)
    lower_bound = fields.Float(required=True)
    upper_bound = fields.Float()
    fixed_amount = fields.Float(default=0.0)
    rate = fields.Float(
        digits=(16, 4),
        required=True,
        help="Use decimal rate values such as 0.18 for 18 percent.",
    )

    @api.depends("rule_set_id.name", "lower_bound", "upper_bound")
    def _compute_name(self):
        for bracket in self:
            upper = bracket.upper_bound if bracket.upper_bound else "Above"
            bracket.name = f"{bracket.rule_set_id.name}: {bracket.lower_bound} - {upper}"


class SecurityPublicHoliday(models.Model):
    _name = "security.public.holiday"
    _description = "Security Public Holiday"
    _order = "holiday_date"

    name = fields.Char(required=True)
    country_code = fields.Char(required=True, default="NA")
    holiday_date = fields.Date(required=True)
    active = fields.Boolean(default=True)
    note = fields.Text()
