from odoo import api, fields, models


class SecurityPayrollRuleSet(models.Model):
    _inherit = "security.payroll.rule.set"

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

    deduction_floor_pct = fields.Float(
        default=0.30,
        string="Minimum Net Pay Floor (%)",
        help="Deductions are capped so net pay never falls below this fraction of gross. E.g. 0.30 means net pay is always at least 30% of gross earnings.",
    )


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

    def _recompute_matching_attendance_records(self, dates):
        if not dates:
            return
        records = self.env["security.attendance.record"].search([
            ("shift_date", "in", list(dates))
        ])
        if records:
            records.modified(["shift_date"])

    @api.model_create_multi
    def create(self, vals_list):
        holidays = super().create(vals_list)
        dates = {h.holiday_date for h in holidays if h.holiday_date}
        self._recompute_matching_attendance_records(dates)
        return holidays

    def write(self, vals):
        old_dates = {h.holiday_date for h in self if h.holiday_date}
        res = super().write(vals)
        if "holiday_date" in vals:
            new_dates = {h.holiday_date for h in self if h.holiday_date}
            self._recompute_matching_attendance_records(old_dates | new_dates)
        return res

    def unlink(self):
        dates = {h.holiday_date for h in self if h.holiday_date}
        res = super().unlink()
        self._recompute_matching_attendance_records(dates)
        return res
