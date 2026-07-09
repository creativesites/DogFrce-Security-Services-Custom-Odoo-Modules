from odoo import api, fields, models
from odoo.exceptions import ValidationError


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


class SecurityContractInvoiceWizard(models.TransientModel):
    """Generate an attendance-based invoice from a client contract + billing period."""
    _name = "security.contract.invoice.wizard"
    _description = "Generate Contract Invoice from Approved Attendance"

    contract_id = fields.Many2one(
        "security.client.contract",
        required=True,
        string="Client Contract",
        domain="[('state', '=', 'active')]",
    )
    partner_id = fields.Many2one(related="contract_id.partner_id", readonly=True)
    site_id = fields.Many2one(related="contract_id.site_id", readonly=True)
    period_month = fields.Date(
        required=True,
        string="Billing Month",
        help="Enter the first day of the month to invoice.",
    )
    vat_rate = fields.Float(default=15.0, string="VAT Rate (%)")
    po_number = fields.Char(string="Client PO Number")

    # Warning flags — computed on-the-fly at wizard load
    warning_exception_count = fields.Integer(
        compute="_compute_warnings",
        string="Unapproved Exceptions",
    )
    warning_message = fields.Char(
        compute="_compute_warnings",
        string="Pre-Invoice Warnings",
    )

    @api.depends("contract_id", "period_month")
    def _compute_warnings(self):
        for wiz in self:
            wiz.warning_exception_count = 0
            wiz.warning_message = ""
            if not wiz.contract_id or not wiz.period_month:
                continue
            from dateutil.relativedelta import relativedelta
            date_from = wiz.period_month.replace(day=1)
            date_to = (date_from + relativedelta(months=1)) - relativedelta(days=1)

            attendance_model = wiz.env.get("security.attendance.record")
            if not attendance_model:
                continue

            domain = [
                ("shift_date", ">=", date_from),
                ("shift_date", "<=", date_to),
                ("partner_id", "=", wiz.contract_id.partner_id.id),
            ]
            if wiz.contract_id.site_id:
                domain.append(("site_id", "=", wiz.contract_id.site_id.id))

            unapproved = attendance_model.search_count(domain + [
                ("has_billing_exception", "=", True),
                ("billing_approved", "=", False),
            ])
            wiz.warning_exception_count = unapproved

            warnings = []
            if unapproved:
                warnings.append(f"{unapproved} attendance exception(s) not yet approved.")
            if wiz.contract_id.state != "active":
                warnings.append("Contract is not active.")
            if wiz.contract_id.date_end and wiz.contract_id.date_end < date_to:
                warnings.append("Contract expires before the end of the billing period.")
            wiz.warning_message = " | ".join(warnings)

    def action_generate(self):
        self.ensure_one()
        from dateutil.relativedelta import relativedelta

        date_from = self.period_month.replace(day=1)
        date_to = (date_from + relativedelta(months=1)) - relativedelta(days=1)

        invoice = self.env["security.billing.invoice"].create({
            "partner_id": self.contract_id.partner_id.id,
            "site_id": self.contract_id.site_id.id if self.contract_id.site_id else False,
            "contract_id": self.contract_id.id,
            "currency_id": self.contract_id.currency_id.id,
            "service_date_from": date_from,
            "service_date_to": date_to,
            "invoice_date": fields.Date.context_today(self),
            "vat_rate": self.vat_rate,
            "po_number": self.po_number or "",
            "generation_source": "attendance",
        })
        invoice.action_generate_from_approved_attendance()

        return {
            "type": "ir.actions.act_window",
            "res_model": "security.billing.invoice",
            "res_id": invoice.id,
            "views": [[False, "form"]],
            "target": "current",
        }
