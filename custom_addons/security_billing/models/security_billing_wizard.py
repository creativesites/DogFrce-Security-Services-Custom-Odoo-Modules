from odoo import api, fields, models


class SecurityBillingInvoiceWizard(models.TransientModel):
    _name = "security.billing.invoice.wizard"
    _description = "Monthly Invoice Generation Wizard"

    billing_plan_id = fields.Many2one("security.billing.plan", required=True, string="Billing Plan")
    partner_id = fields.Many2one(related="billing_plan_id.partner_id", readonly=True)
    period_month = fields.Date(required=True, string="Billing Month (first day)")
    generation_source = fields.Selection(
        [("attendance", "From Attendance Records"), ("roster", "From Roster Slots")],
        default="attendance",
        required=True,
    )
    preview_amount = fields.Float(compute="_compute_preview", string="Estimated Total")

    @api.depends("billing_plan_id", "period_month")
    def _compute_preview(self):
        for wiz in self:
            wiz.preview_amount = 0.0  # Actual computation at confirm time

    def action_generate(self):
        self.ensure_one()
        from dateutil.relativedelta import relativedelta
        date_from = self.period_month.replace(day=1)
        date_to = (date_from + relativedelta(months=1)) - relativedelta(days=1)

        invoice = self.env["security.billing.invoice"].create({
            "billing_plan_id": self.billing_plan_id.id,
            "partner_id": self.billing_plan_id.partner_id.id,
            "service_date_from": date_from,
            "service_date_to": date_to,
            "generation_source": self.generation_source,
        })
        if self.generation_source == "attendance":
            invoice.action_generate_from_attendance()
        else:
            invoice.action_generate_from_roster()

        return {
            "type": "ir.actions.act_window",
            "res_model": "security.billing.invoice",
            "res_id": invoice.id,
            "views": [[False, "form"]],
            "target": "current",
        }
