from odoo import api, fields, models


class SecurityPayrollPeriodWizard(models.TransientModel):
    _name = "security.payroll.period.wizard"
    _description = "Payroll Period Generation Wizard"

    date_from = fields.Date(required=True, string="Period Start")
    date_to = fields.Date(required=True, string="Period End")
    rule_set_id = fields.Many2one("security.payroll.rule.set", required=True, string="Payroll Rule Set")
    eligible_employee_ids = fields.Many2many(
        "hr.employee",
        compute="_compute_eligible_employees",
        string="Eligible Guards",
    )

    @api.depends("date_from", "date_to")
    def _compute_eligible_employees(self):
        for wizard in self:
            if not wizard.date_from or not wizard.date_to:
                wizard.eligible_employee_ids = False
                continue
            # Exclude guards already in an overlapping period
            overlapping_payslips = self.env["security.payslip"].search([
                ("period_id.date_from", "<=", wizard.date_to),
                ("period_id.date_to", ">=", wizard.date_from),
            ])
            already_included = overlapping_payslips.mapped("employee_id").ids
            eligible = self.env["hr.employee"].search([
                ("security_guard", "=", True),
                ("active", "=", True),
                ("id", "not in", already_included),
            ])
            wizard.eligible_employee_ids = eligible

    def action_generate(self):
        self.ensure_one()
        period = self.env["security.payroll.period"].create({
            "date_from": self.date_from,
            "date_to": self.date_to,
            "rule_set_id": self.rule_set_id.id,
        })
        period.action_generate_payslips()
        return {
            "type": "ir.actions.act_window",
            "res_model": "security.payroll.period",
            "res_id": period.id,
            "views": [[False, "form"]],
            "target": "current",
        }
