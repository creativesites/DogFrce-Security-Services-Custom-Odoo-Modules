import base64
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SecurityBillingPlan(models.Model):
    _name = "security.billing.plan"
    _description = "Security Billing Plan"
    _order = "partner_id, name"

    name = fields.Char(required=True)
    partner_id = fields.Many2one("res.partner", required=True, string="Client")
    currency_id = fields.Many2one(
        "res.currency",
        required=True,
        default=lambda self: self.env.company.currency_id.id,
    )
    billing_mode = fields.Selection(
        [
            ("recurring", "Recurring Contract"),
            ("shift", "Per Shift"),
            ("adhoc", "Ad Hoc Service"),
        ],
        default="recurring",
        required=True,
    )
    date_start = fields.Date(required=True)
    date_end = fields.Date()
    payment_term_days = fields.Integer(default=30)
    vat_rate = fields.Float(default=15.0)
    active = fields.Boolean(default=True)
    auto_invoice = fields.Boolean(default=False, string="Auto-Invoice Monthly")
    line_ids = fields.One2many(
        "security.billing.plan.line",
        "billing_plan_id",
        string="Billing Lines",
    )
    note = fields.Text()

    @api.model
    def action_auto_invoice_all(self):
        """Cron: auto-generate monthly draft invoices for qualifying billing plans."""
        from datetime import date
        import calendar

        today = date.today()
        first_day = today.replace(day=1)
        last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])

        plans = self.search([("active", "=", True), ("auto_invoice", "=", True)])
        invoice_model = self.env["security.billing.invoice"]

        for plan in plans:
            existing = invoice_model.search([
                ("billing_plan_id", "=", plan.id),
                ("service_date_from", "=", str(first_day)),
                ("service_date_to", "=", str(last_day)),
            ], limit=1)
            if existing:
                continue

            due = first_day + timedelta(days=plan.payment_term_days)
            invoice_model.create({
                "name": "New",
                "partner_id": plan.partner_id.id,
                "billing_plan_id": plan.id,
                "currency_id": plan.currency_id.id,
                "vat_rate": plan.vat_rate,
                "state": "draft",
                "generation_source": "manual",
                "invoice_date": str(today),
                "due_date": str(due),
                "service_date_from": str(first_day),
                "service_date_to": str(last_day),
            })

        return True

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for plan in self:
            if plan.date_end and plan.date_end < plan.date_start:
                raise ValidationError("Billing plan end date cannot be earlier than start date.")

    @api.constrains("payment_term_days", "vat_rate")
    def _check_billing_settings(self):
        for plan in self:
            if plan.payment_term_days < 0:
                raise ValidationError("Payment term days cannot be negative.")
            if plan.vat_rate < 0:
                raise ValidationError("VAT rate cannot be negative.")


class SecurityBillingPlanLine(models.Model):
    _name = "security.billing.plan.line"
    _description = "Security Billing Plan Line"
    _order = "sequence, id"

    billing_plan_id = fields.Many2one(
        "security.billing.plan",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    post_id = fields.Many2one("security.post")
    post_type_id = fields.Many2one("security.post.type")
    billing_basis = fields.Selection(
        [
            ("monthly", "Monthly Fixed"),
            ("shift", "Per Shift"),
            ("guard_shift", "Per Guard Per Shift"),
        ],
        default="monthly",
        required=True,
    )
    quantity = fields.Float(default=1.0)
    unit_price = fields.Float(required=True, default=0.0)
    guard_count = fields.Integer(default=1)
    shift_template_id = fields.Many2one("security.shift.template")
    subtotal = fields.Float(
        compute="_compute_subtotal",
        store=True,
    )
    note = fields.Text()

    @api.depends("quantity", "unit_price", "guard_count", "billing_basis")
    def _compute_subtotal(self):
        for line in self:
            multiplier = line.guard_count if line.billing_basis == "guard_shift" else 1.0
            line.subtotal = line.quantity * line.unit_price * multiplier

    @api.constrains("quantity", "unit_price", "guard_count")
    def _check_line_values(self):
        for line in self:
            if line.quantity < 0:
                raise ValidationError("Billing line quantity cannot be negative.")
            if line.unit_price < 0:
                raise ValidationError("Billing line unit price cannot be negative.")
            if line.guard_count < 0:
                raise ValidationError("Guard count cannot be negative.")


class SecurityBillingInvoice(models.Model):
    _name = "security.billing.invoice"
    _description = "Security Billing Invoice"
    _order = "invoice_date desc, id desc"
    _rec_name = "name"

    name = fields.Char(required=True)
    partner_id = fields.Many2one("res.partner", required=True, string="Client")
    billing_plan_id = fields.Many2one("security.billing.plan")
    service_date_from = fields.Date()
    service_date_to = fields.Date()
    site_id = fields.Many2one("security.client.site", string="Client Site")
    generation_source = fields.Selection(
        [
            ("manual", "Manual"),
            ("roster", "Roster"),
            ("attendance", "Attendance"),
        ],
        default="manual",
        required=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        required=True,
        default=lambda self: self.env.company.currency_id.id,
    )
    invoice_date = fields.Date(required=True, default=fields.Date.context_today)
    due_date = fields.Date()
    po_number = fields.Char(string="Purchase Order Number")
    vat_rate = fields.Float(default=15.0)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("sent", "Sent"),
            ("paid", "Paid"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
    )
    line_ids = fields.One2many(
        "security.billing.invoice.line",
        "invoice_id",
        string="Invoice Lines",
    )
    roster_slot_ids = fields.Many2many(
        "security.roster.slot",
        "security_billing_invoice_roster_rel",
        "invoice_id",
        "roster_slot_id",
        string="Roster Slots",
    )
    attendance_record_ids = fields.Many2many(
        "security.attendance.record",
        "security_billing_invoice_attendance_rel",
        "invoice_id",
        "attendance_id",
        string="Attendance Records",
    )
    subtotal_amount = fields.Float(
        compute="_compute_totals",
        store=True,
    )
    vat_amount = fields.Float(
        compute="_compute_totals",
        store=True,
    )
    total_amount = fields.Float(
        compute="_compute_totals",
        store=True,
    )
    amount_in_words = fields.Char(
        compute="_compute_amount_in_words",
        store=True,
    )
    note = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == "New":
                vals["name"] = sequence.next_by_code("security.billing.invoice") or "New"
        return super().create(vals_list)

    @api.depends("line_ids.subtotal", "vat_rate")
    def _compute_totals(self):
        for invoice in self:
            subtotal = sum(invoice.line_ids.mapped("subtotal"))
            invoice.subtotal_amount = subtotal
            invoice.vat_amount = subtotal * (invoice.vat_rate / 100.0)
            invoice.total_amount = invoice.subtotal_amount + invoice.vat_amount

    @api.depends("total_amount", "currency_id")
    def _compute_amount_in_words(self):
        for invoice in self:
            amount = int(round(invoice.total_amount))
            currency_name = invoice.currency_id.name or "Currency"
            invoice.amount_in_words = f"{amount} {currency_name} Only"

    @api.onchange("billing_plan_id")
    def _onchange_billing_plan_id(self):
        if not self.billing_plan_id:
            return
        self.partner_id = self.billing_plan_id.partner_id
        self.currency_id = self.billing_plan_id.currency_id
        self.vat_rate = self.billing_plan_id.vat_rate
        if self.invoice_date and self.billing_plan_id.payment_term_days:
            self.due_date = self.invoice_date + timedelta(days=self.billing_plan_id.payment_term_days)

    @api.onchange("invoice_date")
    def _onchange_invoice_date(self):
        for invoice in self:
            if invoice.invoice_date and invoice.billing_plan_id:
                invoice.due_date = invoice.invoice_date + timedelta(
                    days=invoice.billing_plan_id.payment_term_days
                )

    @api.constrains("due_date", "invoice_date")
    def _check_due_date(self):
        for invoice in self:
            if invoice.due_date and invoice.due_date < invoice.invoice_date:
                raise ValidationError("Invoice due date cannot be earlier than invoice date.")

    @api.constrains("vat_rate")
    def _check_invoice_values(self):
        for invoice in self:
            if invoice.vat_rate < 0:
                raise ValidationError("VAT rate cannot be negative.")

    @api.constrains("service_date_from", "service_date_to")
    def _check_service_dates(self):
        for invoice in self:
            if invoice.service_date_from and invoice.service_date_to and invoice.service_date_to < invoice.service_date_from:
                raise ValidationError("Service end date cannot be earlier than service start date.")

    def _get_generation_domain(self):
        self.ensure_one()
        if not self.service_date_from or not self.service_date_to:
            raise ValidationError("Set the service start and end dates before generating invoice lines.")
        domain = [
            ("shift_date", ">=", self.service_date_from),
            ("shift_date", "<=", self.service_date_to),
        ]
        if self.partner_id:
            domain.append(("partner_id", "=", self.partner_id.id))
        if self.site_id:
            domain.append(("site_id", "=", self.site_id.id))
        return domain

    def _prepare_grouped_invoice_lines(self, source_records):
        grouped = {}
        for record in source_records:
            slot = record.roster_slot_id if record._name == "security.attendance.record" else record
            requirement = slot.shift_requirement_id
            post = slot.post_id
            template = slot.shift_template_id
            bill_rate = requirement.bill_rate if requirement else 0.0
            if bill_rate <= 0:
                continue
            key = (
                post.site_id.id if post.site_id else False,
                post.id,
                template.id,
                bill_rate,
            )
            if key not in grouped:
                grouped[key] = {
                    "site": post.site_id.name if post.site_id else "",
                    "post": post.name or "",
                    "template": template.name or "",
                    "shift_template_id": template.id,
                    "quantity": 0.0,
                    "unit_price": bill_rate,
                    "service_date_from": self.service_date_from,
                    "service_date_to": self.service_date_to,
                }
            grouped[key]["quantity"] += 1.0

        invoice_lines = []
        for values in grouped.values():
            label_parts = [values["site"], values["post"], values["template"]]
            invoice_lines.append(
                (
                    0,
                    0,
                    {
                        "name": " - ".join(part for part in label_parts if part),
                        "service_date_from": values["service_date_from"],
                        "service_date_to": values["service_date_to"],
                        "site_id": key[0],
                        "post_id": key[1],
                        "guard_count": 1,
                        "shift_template_id": values["shift_template_id"],
                        "quantity": values["quantity"],
                        "unit_price": values["unit_price"],
                    },
                )
            )
        return invoice_lines

    def action_generate_from_roster(self):
        roster_model = self.env["security.roster.slot"]
        for invoice in self:
            slots = roster_model.search(invoice._get_generation_domain() + [("state", "!=", "cancelled")])
            if not slots:
                raise ValidationError("No roster slots found for this invoice period.")
            lines = invoice._prepare_grouped_invoice_lines(slots)
            if not lines:
                raise ValidationError("No billable roster slots found. Check shift requirement bill rates.")
            invoice.line_ids.unlink()
            invoice.roster_slot_ids = [(6, 0, slots.ids)]
            invoice.attendance_record_ids = [(5, 0, 0)]
            invoice.line_ids = lines
            invoice.generation_source = "roster"

    def action_generate_from_attendance(self):
        attendance_model = self.env["security.attendance.record"]
        for invoice in self:
            records = attendance_model.search(
                invoice._get_generation_domain()
                + [
                    ("status", "in", ("present", "late", "early_leave")),
                ]
            )
            if not records:
                raise ValidationError("No billable attendance records found for this invoice period.")
            lines = invoice._prepare_grouped_invoice_lines(records)
            if not lines:
                raise ValidationError("No billable attendance records found. Check shift requirement bill rates.")
            invoice.line_ids.unlink()
            invoice.attendance_record_ids = [(6, 0, records.ids)]
            invoice.roster_slot_ids = [(6, 0, records.mapped("roster_slot_id").ids)]
            invoice.line_ids = lines
            invoice.generation_source = "attendance"

    def action_mark_sent(self):
        for invoice in self:
            if not invoice.line_ids:
                raise ValidationError("Add at least one invoice line before marking the invoice as sent.")
            invoice.state = "sent"

    def action_mark_paid(self):
        for invoice in self:
            invoice.state = "paid"

    def action_cancel(self):
        for invoice in self:
            invoice.state = "cancelled"

    def action_reset_to_draft(self):
        for invoice in self:
            invoice.state = "draft"

    def action_send_invoice_email(self):
        self.ensure_one()
        partner = self.partner_id
        if not partner or not partner.email:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {"title": "No Email", "message": "Client has no email address configured.", "type": "warning"},
            }
        try:
            report = self.env.ref("security_billing.action_report_security_invoice")
            pdf_content, _ = report._render_qweb_pdf([self.id])
            attachment = self.env["ir.attachment"].create({
                "name": f"Invoice_{self.name.replace('/', '_')}.pdf",
                "type": "binary",
                "datas": base64.b64encode(pdf_content),
                "res_model": "security.billing.invoice",
                "res_id": self.id,
            })
            mail = self.env["mail.mail"].create({
                "subject": f"Invoice {self.name} — DogForce Security Services",
                "email_to": partner.email,
                "body_html": f"""
                    <p>Dear {partner.name},</p>
                    <p>Please find attached your invoice <strong>{self.name}</strong> for the period {self.service_date_from} to {self.service_date_to}.</p>
                    <p><strong>Total Amount: {self.currency_id.symbol} {self.total_amount:,.2f}</strong></p>
                    <p>Payment is due within the agreed payment terms. Please reference invoice number <strong>{self.name}</strong> when making payment.</p>
                    <p>For queries, please contact us directly.</p>
                    <p>Regards,<br/>DogForce Security Services</p>
                """,
                "attachment_ids": [(4, attachment.id)],
            })
            mail.send()
            self.state = "sent"
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {"title": "Invoice Sent", "message": f"Invoice emailed to {partner.email}.", "type": "success"},
            }
        except Exception as e:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {"title": "Send Failed", "message": str(e)[:200], "type": "danger"},
            }

    def action_create_credit_note(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "security.billing.credit.note",
            "views": [[False, "form"]],
            "context": {"default_invoice_id": self.id},
            "target": "new",
        }

    def action_print_aging(self):
        unpaid = self.search([("state", "not in", ["paid", "cancelled"]), ("due_date", "!=", False)])
        return self.env.ref("security_billing.action_report_security_invoice_aging").report_action(unpaid)

    def action_preview_pdf(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/report/html/security_billing.report_security_billing_invoice/{self.id}",
            "target": "new",
        }


class SecurityBillingInvoiceLine(models.Model):
    _name = "security.billing.invoice.line"
    _description = "Security Billing Invoice Line"
    _order = "sequence, id"

    invoice_id = fields.Many2one(
        "security.billing.invoice",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    service_date_from = fields.Date()
    service_date_to = fields.Date()
    guard_count = fields.Integer(default=1)
    site_id = fields.Many2one("security.client.site", string="Client Site")
    post_id = fields.Many2one("security.post", string="Post")
    shift_template_id = fields.Many2one("security.shift.template")
    quantity = fields.Float(default=1.0)
    unit_price = fields.Float(default=0.0)
    subtotal = fields.Float(
        compute="_compute_subtotal",
        store=True,
    )
    note = fields.Text()

    @api.depends("quantity", "unit_price", "guard_count")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_price * max(line.guard_count, 1)

    @api.constrains("service_date_from", "service_date_to", "quantity", "unit_price", "guard_count")
    def _check_invoice_line_values(self):
        for line in self:
            if line.service_date_from and line.service_date_to and line.service_date_to < line.service_date_from:
                raise ValidationError("Service end date cannot be earlier than service start date.")
            if line.quantity < 0:
                raise ValidationError("Invoice line quantity cannot be negative.")
            if line.unit_price < 0:
                raise ValidationError("Invoice line unit price cannot be negative.")
            if line.guard_count < 0:
                raise ValidationError("Invoice line guard count cannot be negative.")


class SecurityBillingCreditNote(models.Model):
    _name = "security.billing.credit.note"
    _description = "Security Billing Credit Note"
    _order = "date desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    invoice_id = fields.Many2one(
        "security.billing.invoice",
        required=True,
        string="Original Invoice",
        ondelete="restrict",
    )
    partner_id = fields.Many2one(related="invoice_id.partner_id", store=True, readonly=True)
    currency_id = fields.Many2one(related="invoice_id.currency_id", store=True, readonly=True)
    date = fields.Date(required=True, default=fields.Date.context_today)
    amount = fields.Float(required=True, string="Credit Amount")
    reason = fields.Text(required=True, string="Reason for Credit")
    state = fields.Selection(
        [("draft", "Draft"), ("confirmed", "Confirmed"), ("applied", "Applied")],
        default="draft",
    )

    @api.depends("invoice_id", "date")
    def _compute_name(self):
        for cn in self:
            invoice = cn.invoice_id.name or "Draft"
            cn.name = f"CN/{invoice}/{cn.date or ''}"

    def action_confirm(self):
        for cn in self:
            cn.state = "confirmed"

    def action_apply(self):
        for cn in self:
            cn.state = "applied"

    def action_reset_to_draft(self):
        for cn in self:
            cn.state = "draft"


class SecurityBillingDashboard(models.AbstractModel):
    """Abstract model — provides the Billing Command Center dashboard data."""
    _name = "security.billing.dashboard"
    _description = "Billing Dashboard Data Provider"

    @api.model
    def get_dashboard_data(self):
        from datetime import date as _date
        today = _date.today()
        month_start = today.replace(day=1)

        Invoice = self.env["security.billing.invoice"]

        active_plans = self.env["security.billing.plan"].search([("active", "=", True)])

        mtd_invoices = Invoice.search([
            ("invoice_date", ">=", month_start),
            ("state", "not in", ["cancelled"]),
        ])
        invoiced_mtd = sum(mtd_invoices.mapped("total_amount"))
        collected_mtd = sum(
            mtd_invoices.filtered(lambda i: i.state == "paid").mapped("total_amount")
        )

        outstanding = Invoice.search([("state", "not in", ["paid", "cancelled"])])
        outstanding_total = sum(outstanding.mapped("total_amount"))
        overdue_total = sum(
            outstanding.filtered(
                lambda i: i.due_date and i.due_date < today
            ).mapped("total_amount")
        )

        plans_data = []
        for plan in active_plans:
            last_inv = Invoice.search(
                [("billing_plan_id", "=", plan.id), ("state", "!=", "cancelled")],
                order="invoice_date desc",
                limit=1,
            )
            plans_data.append({
                "id": plan.id,
                "name": plan.name,
                "client": plan.partner_id.name,
                "mode": dict(self.env["security.billing.plan"]._fields["billing_mode"].selection).get(plan.billing_mode, plan.billing_mode),
                "last_inv_date": str(last_inv.invoice_date) if last_inv and last_inv.invoice_date else "",
                "last_inv_total": last_inv.total_amount if last_inv else 0.0,
                "last_inv_state": last_inv.state if last_inv else "",
                "last_inv_due": str(last_inv.due_date) if last_inv and last_inv.due_date else "",
                "last_inv_id": last_inv.id if last_inv else 0,
                "is_overdue": bool(last_inv and last_inv.due_date and last_inv.due_date < today and last_inv.state not in ("paid", "cancelled")),
            })

        recent_data = [{
            "id": i.id,
            "name": i.name,
            "client": i.partner_id.name,
            "date": str(i.invoice_date) if i.invoice_date else "",
            "due": str(i.due_date) if i.due_date else "",
            "total": i.total_amount,
            "state": i.state,
            "overdue": bool(i.due_date and i.due_date < today and i.state not in ("paid", "cancelled")),
        } for i in Invoice.search(
            [("state", "not in", ["cancelled"])],
            order="invoice_date desc",
            limit=12,
        )]

        return {
            "month_label": today.strftime("%B %Y"),
            "active_plan_count": len(active_plans),
            "invoiced_mtd": invoiced_mtd,
            "collected_mtd": collected_mtd,
            "outstanding_total": outstanding_total,
            "overdue_total": overdue_total,
            "plans": plans_data,
            "recent_invoices": recent_data,
        }
