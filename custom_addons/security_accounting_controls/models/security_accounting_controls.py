from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SecurityBillingInvoice(models.Model):
    _inherit = "security.billing.invoice"

    payment_ids = fields.One2many(
        "security.client.payment",
        "invoice_id",
        string="Payments",
    )
    paid_amount = fields.Float(
        compute="_compute_payment_status",
        store=True,
    )
    balance_amount = fields.Float(
        compute="_compute_payment_status",
        store=True,
    )
    payment_status = fields.Selection(
        [
            ("unpaid", "Unpaid"),
            ("partial", "Partially Paid"),
            ("paid", "Paid"),
            ("overpaid", "Overpaid"),
        ],
        compute="_compute_payment_status",
        store=True,
    )
    days_overdue = fields.Integer(
        compute="_compute_ageing",
        store=True,
    )
    ageing_bucket = fields.Selection(
        [
            ("current", "Current"),
            ("1_30", "1-30 Days"),
            ("31_60", "31-60 Days"),
            ("61_90", "61-90 Days"),
            ("90_plus", "90+ Days"),
        ],
        compute="_compute_ageing",
        store=True,
    )

    @api.depends("payment_ids.amount", "payment_ids.state", "total_amount")
    def _compute_payment_status(self):
        for invoice in self:
            paid_amount = sum(
                invoice.payment_ids.filtered(lambda payment: payment.state != "cancelled").mapped("amount")
            )
            balance = invoice.total_amount - paid_amount
            invoice.paid_amount = paid_amount
            invoice.balance_amount = balance
            if paid_amount <= 0:
                invoice.payment_status = "unpaid"
            elif balance > 0.01:
                invoice.payment_status = "partial"
            elif balance < -0.01:
                invoice.payment_status = "overpaid"
            else:
                invoice.payment_status = "paid"

    def action_open_record_payment(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "security.record.payment.wizard",
            "views": [[False, "form"]],
            "context": {"default_invoice_id": self.id},
            "target": "new",
        }

    @api.depends("due_date", "state", "payment_status")
    def _compute_ageing(self):
        today = fields.Date.context_today(self)
        for invoice in self:
            if not invoice.due_date or invoice.payment_status == "paid" or invoice.state == "cancelled":
                overdue_days = 0
            else:
                overdue_days = max((today - invoice.due_date).days, 0)
            invoice.days_overdue = overdue_days
            if overdue_days == 0:
                invoice.ageing_bucket = "current"
            elif overdue_days <= 30:
                invoice.ageing_bucket = "1_30"
            elif overdue_days <= 60:
                invoice.ageing_bucket = "31_60"
            elif overdue_days <= 90:
                invoice.ageing_bucket = "61_90"
            else:
                invoice.ageing_bucket = "90_plus"


class SecurityClientPayment(models.Model):
    _name = "security.client.payment"
    _description = "Security Client Payment"
    _order = "payment_date desc, id desc"
    _rec_name = "reference"

    reference = fields.Char(required=True, default="New")
    invoice_id = fields.Many2one(
        "security.billing.invoice",
        required=True,
        ondelete="restrict",
    )
    partner_id = fields.Many2one(
        related="invoice_id.partner_id",
        store=True,
        readonly=True,
        string="Client",
    )
    currency_id = fields.Many2one(
        related="invoice_id.currency_id",
        store=True,
        readonly=True,
    )
    payment_date = fields.Date(required=True, default=fields.Date.context_today)
    amount = fields.Float(required=True)
    payment_method = fields.Selection(
        [
            ("bank_transfer", "Bank Transfer"),
            ("cash", "Cash"),
            ("cheque", "Cheque"),
            ("mobile_money", "Mobile Money"),
            ("other", "Other"),
        ],
        default="bank_transfer",
        required=True,
    )
    bank_reference = fields.Char()
    received_by_id = fields.Many2one(
        "res.users",
        default=lambda self: self.env.user.id,
        string="Received By",
    )
    reconciliation_status = fields.Selection(
        [
            ("unmatched", "Unmatched"),
            ("matched", "Matched"),
            ("exception", "Exception"),
        ],
        default="unmatched",
        required=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("posted", "Posted"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
    )
    note = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if not vals.get("reference") or vals.get("reference") == "New":
                vals["reference"] = sequence.next_by_code("security.client.payment") or "New"
        return super().create(vals_list)

    @api.constrains("amount")
    def _check_amount(self):
        for payment in self:
            if payment.amount <= 0:
                raise ValidationError("Payment amount must be greater than zero.")

    def action_post(self):
        for payment in self:
            payment.state = "posted"
            payment.invoice_id._compute_payment_status()
            if payment.invoice_id.payment_status == "paid":
                payment.invoice_id.state = "paid"

    def action_match_bank_reference(self):
        for payment in self:
            if not payment.bank_reference:
                raise ValidationError("Add a bank reference before marking this payment as matched.")
            payment.reconciliation_status = "matched"

    def action_flag_exception(self):
        for payment in self:
            payment.reconciliation_status = "exception"

    def action_cancel(self):
        for payment in self:
            payment.state = "cancelled"
            payment.invoice_id._compute_payment_status()


class SecurityRecordPaymentWizard(models.TransientModel):
    _name = "security.record.payment.wizard"
    _description = "Record Payment Wizard"

    invoice_id = fields.Many2one("security.billing.invoice", required=True, readonly=True)
    partner_id = fields.Many2one(related="invoice_id.partner_id", readonly=True)
    invoice_total = fields.Float(related="invoice_id.total_amount", readonly=True, string="Invoice Total")
    outstanding = fields.Float(compute="_compute_outstanding", string="Amount Outstanding")
    amount = fields.Float(required=True, string="Payment Amount")
    payment_date = fields.Date(required=True, default=fields.Date.context_today)
    payment_method = fields.Selection(
        [
            ("bank_transfer", "Bank Transfer"),
            ("cash", "Cash"),
            ("cheque", "Cheque"),
            ("mobile_money", "Mobile Money"),
            ("other", "Other"),
        ],
        default="bank_transfer",
        required=True,
    )
    bank_reference = fields.Char(string="Bank Reference / Transaction ID")
    note = fields.Text()

    @api.depends("invoice_id")
    def _compute_outstanding(self):
        for wiz in self:
            invoice = wiz.invoice_id
            if invoice:
                paid = sum(
                    invoice.payment_ids.filtered(lambda p: p.state == "posted").mapped("amount")
                ) if hasattr(invoice, "payment_ids") else 0.0
                wiz.outstanding = max(0, invoice.total_amount - paid)
            else:
                wiz.outstanding = 0.0

    @api.onchange("invoice_id")
    def _onchange_invoice(self):
        if self.invoice_id:
            self.amount = self.outstanding or self.invoice_id.total_amount

    def action_record_payment(self):
        self.ensure_one()
        payment = self.env["security.client.payment"].create({
            "invoice_id": self.invoice_id.id,
            "amount": self.amount,
            "payment_date": self.payment_date,
            "payment_method": self.payment_method,
            "bank_reference": self.bank_reference or False,
            "note": self.note or False,
        })
        payment.action_post()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Payment Recorded",
                "message": f"Payment of N$ {self.amount:,.2f} recorded for {self.invoice_id.name}.",
                "type": "success",
            },
        }


class ResPartner(models.Model):
    _inherit = "res.partner"

    security_invoice_outstanding = fields.Float(
        compute="_compute_invoice_outstanding",
        string="Outstanding (Security)",
    )
    security_invoice_count = fields.Integer(
        compute="_compute_invoice_outstanding",
        string="Security Invoices",
    )

    def _compute_invoice_outstanding(self):
        invoice_model = self.env.get("security.billing.invoice")
        for partner in self:
            if invoice_model is not None:
                unpaid = invoice_model.search([
                    ("partner_id", "=", partner.id),
                    ("state", "not in", ["paid", "cancelled"]),
                ])
                partner.security_invoice_outstanding = sum(unpaid.mapped("total_amount"))
                partner.security_invoice_count = len(unpaid)
            else:
                partner.security_invoice_outstanding = 0
                partner.security_invoice_count = 0
