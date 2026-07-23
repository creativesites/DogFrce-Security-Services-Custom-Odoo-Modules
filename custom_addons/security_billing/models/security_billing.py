import base64
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SecurityBillingPlan(models.Model):
    _name = "security.billing.plan"
    _description = "Security Billing Plan"
    _order = "partner_id, name"

    name = fields.Char(required=True)
    partner_id = fields.Many2one("res.partner", required=True, string="Client", domain=[("is_company", "=", True)])
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

    @api.onchange("post_id")
    def _onchange_post_id(self):
        for line in self:
            if line.post_id:
                if line.post_id.post_type_id:
                    line.post_type_id = line.post_id.post_type_id
                if not line.name:
                    line.name = line.post_id.name

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
    partner_id = fields.Many2one("res.partner", required=True, string="Client", domain=[("is_company", "=", True)])
    billing_plan_id = fields.Many2one("security.billing.plan")
    service_date_from = fields.Date()
    service_date_to = fields.Date()
    site_id = fields.Many2one("security.client.site", string="Client Site", domain="[('partner_id','=',partner_id)]")
    contract_id = fields.Many2one(
        "security.client.contract",
        string="Client Contract",
        domain="[('partner_id','=',partner_id)]",
        help="When generating from approved attendance, uses this contract's rate card.",
    )
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

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        for invoice in self:
            if invoice.site_id and invoice.site_id.partner_id != invoice.partner_id:
                invoice.site_id = False
            if invoice.contract_id and invoice.contract_id.partner_id != invoice.partner_id:
                invoice.contract_id = False
            if invoice.billing_plan_id and invoice.billing_plan_id.partner_id != invoice.partner_id:
                invoice.billing_plan_id = False
            if invoice.line_ids:
                for line in invoice.line_ids:
                    if line.site_id and line.site_id.partner_id != invoice.partner_id:
                        line.site_id = False
                    if line.post_id and line.post_id.site_id.partner_id != invoice.partner_id:
                        line.post_id = False

    @api.onchange("site_id")
    def _onchange_site_id(self):
        for invoice in self:
            if invoice.site_id:
                if not invoice.partner_id or invoice.site_id.partner_id != invoice.partner_id:
                    invoice.partner_id = invoice.site_id.partner_id
                contract_model = self.env.get("security.client.contract")
                if contract_model and not invoice.contract_id:
                    today = invoice.invoice_date or fields.Date.context_today(self)
                    active_contract = contract_model.get_active_for_site(invoice.site_id, today)
                    if active_contract:
                        invoice.contract_id = active_contract.id

    @api.onchange("contract_id")
    def _onchange_contract_id(self):
        for invoice in self:
            if invoice.contract_id:
                if not invoice.partner_id or invoice.contract_id.partner_id != invoice.partner_id:
                    invoice.partner_id = invoice.contract_id.partner_id
                if invoice.contract_id.site_id and not invoice.site_id:
                    invoice.site_id = invoice.contract_id.site_id

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

    # (field_name, display_label, rule_set_multiplier_attr)
    _PREMIUM_BUCKETS = [
        ("normal_hours",         "Normal Hours",         None),
        ("saturday_hours",       "Saturday Hours",       "saturday_multiplier"),
        ("sunday_hours",         "Sunday Hours",         "sunday_multiplier"),
        ("public_holiday_hours", "Public Holiday Hours", "public_holiday_multiplier"),
        ("night_hours",          "Night Shift Hours",    "night_shift_multiplier"),
    ]

    def _get_billing_rule_set(self):
        if "security.payroll.rule.set" not in self.env:
            return None
        country_code = self.env.company.country_id.code if self.env.company.country_id else None
        domain = [("country_code", "=", country_code)] if country_code else []
        return self.env["security.payroll.rule.set"].search(domain, order="id desc", limit=1)

    def _prepare_grouped_invoice_lines(self, source_records):
        if not source_records:
            return []
        if source_records._name == "security.attendance.record":
            return self._prepare_attendance_invoice_lines(source_records)
        return self._prepare_roster_invoice_lines(source_records)

    def _prepare_attendance_invoice_lines(self, records):
        """Invoice lines split by premium bucket using actual payable hours."""
        rule_set = self._get_billing_rule_set()
        grouped = {}
        for rec in records:
            slot = rec.roster_slot_id
            if not slot:
                continue
            requirement = slot.shift_requirement_id
            post = slot.post_id
            template = slot.shift_template_id
            if not post or not template:
                continue
            bill_rate = requirement.bill_rate if requirement else 0.0
            if bill_rate <= 0:
                continue
            site_prefix = (post.site_id.name + " — ") if post.site_id else ""
            for field_name, label, mult_attr in self._PREMIUM_BUCKETS:
                hours = getattr(rec, field_name, 0.0)
                if not hours:
                    continue
                multiplier = (
                    getattr(rule_set, mult_attr, 1.0) if rule_set and mult_attr else 1.0
                )
                key = (post.site_id.id or False, post.id, template.id, field_name)
                if key not in grouped:
                    grouped[key] = {
                        "name": f"{site_prefix}{post.name or ''} ({label})",
                        "site_id": post.site_id.id or False,
                        "post_id": post.id,
                        "shift_template_id": template.id,
                        "quantity": 0.0,
                        "unit_price": bill_rate * multiplier,
                        "service_date_from": self.service_date_from,
                        "service_date_to": self.service_date_to,
                    }
                grouped[key]["quantity"] += hours
        return [(0, 0, v) for v in grouped.values() if v["quantity"] > 0]

    def _prepare_roster_invoice_lines(self, slots):
        """Invoice lines grouped by post/template, counting shifts."""
        grouped = {}
        for slot in slots:
            requirement = slot.shift_requirement_id
            post = slot.post_id
            template = slot.shift_template_id
            bill_rate = requirement.bill_rate if requirement else 0.0
            if bill_rate <= 0:
                continue
            key = (post.site_id.id or False, post.id, template.id, bill_rate)
            if key not in grouped:
                site_name = post.site_id.name if post.site_id else ""
                grouped[key] = {
                    "name": " - ".join(p for p in [site_name, post.name or "", template.name or ""] if p),
                    "site_id": post.site_id.id or False,
                    "post_id": post.id,
                    "shift_template_id": template.id,
                    "quantity": 0.0,
                    "unit_price": bill_rate,
                    "service_date_from": self.service_date_from,
                    "service_date_to": self.service_date_to,
                }
            grouped[key]["quantity"] += 1.0
        return [(0, 0, v) for v in grouped.values()]

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

    def action_generate_from_approved_attendance(self):
        """Generate invoice lines from contract rate cards using billing-approved attendance."""
        contract_model = self.env.get("security.client.contract")
        if not contract_model:
            raise ValidationError("The contracts module (security_operations) is not installed.")

        _CATEGORY_LABELS = {
            "normal": "Normal / Day",
            "night": "Night Shift",
            "saturday": "Saturday",
            "sunday": "Sunday",
            "public_holiday": "Public Holiday",
        }

        for invoice in self:
            if not invoice.service_date_from or not invoice.service_date_to:
                raise ValidationError("Set service dates before generating invoice lines.")

            domain = invoice._get_generation_domain()
            # Include records that are present/late/early_leave AND either have no exception
            # or have an exception that has been billing-approved.
            domain += [("status", "in", ("present", "late", "early_leave"))]
            domain += [
                "|",
                ("has_billing_exception", "=", False),
                "&",
                ("has_billing_exception", "=", True),
                ("billing_approved", "=", True),
            ]

            records = self.env["security.attendance.record"].search(domain)
            if not records:
                raise ValidationError(
                    "No billable attendance records found for this period. "
                    "Ensure guards have check-in/out data and billing exceptions are approved."
                )

            lines_data = {}
            included_record_ids = []

            for rec in records:
                if not rec.site_id or not rec.shift_date:
                    continue
                contract = invoice.contract_id or contract_model.get_active_for_site(
                    rec.site_id, rec.shift_date
                )
                if not contract:
                    continue
                grade = rec.employee_id.security_grade_id if rec.employee_id else None
                grade_name = grade.name if grade else "Standard"
                site_name = rec.site_id.name if rec.site_id else "Unknown Site"

                buckets = {
                    "normal": (rec.normal_hours or 0.0),
                    "night": (rec.night_hours or 0.0),
                    "saturday": (rec.saturday_hours or 0.0),
                    "sunday": (rec.sunday_hours or 0.0),
                    "public_holiday": (rec.public_holiday_hours or 0.0),
                }
                if rec.overtime_approved and rec.overtime_hours:
                    buckets["normal"] += rec.overtime_hours

                for cat, hours in buckets.items():
                    if not hours:
                        continue
                    rate = contract.get_rate_for(grade, cat)
                    if not rate:
                        continue
                    key = (rec.site_id.id, grade.id if grade else False, cat)
                    if key not in lines_data:
                        lines_data[key] = {
                            "name": f"{site_name} — {grade_name} ({_CATEGORY_LABELS[cat]})",
                            "site_id": rec.site_id.id if rec.site_id else False,
                            "quantity": 0.0,
                            "unit_price": rate,
                            "service_date_from": invoice.service_date_from,
                            "service_date_to": invoice.service_date_to,
                        }
                    else:
                        # Use the highest rate found (handles multiple contracts with different rates)
                        lines_data[key]["unit_price"] = max(lines_data[key]["unit_price"], rate)
                    lines_data[key]["quantity"] += hours
                included_record_ids.append(rec.id)

            if not lines_data:
                raise ValidationError(
                    "No billable hours found. Ensure contracts have rate cards configured."
                )

            invoice.line_ids.unlink()
            invoice.attendance_record_ids = [(6, 0, included_record_ids)]
            invoice.roster_slot_ids = [(5, 0, 0)]
            invoice.line_ids = [
                (0, 0, {**v, "quantity": round(v["quantity"], 2)})
                for v in lines_data.values()
                if v["quantity"] > 0
            ]
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

    @api.model
    def get_revenue_dashboard_data(self):
        """Server-side data for the Revenue Dashboard OWL component."""
        import calendar
        from datetime import date, timedelta
        from collections import defaultdict

        today = date.today()
        mtd_start = today.replace(day=1)
        mtd_end = today

        # Approved attendance billing (MTD) — sum billing_amount from attendance records
        # billing_amount is non-stored, so we pull the stored hour buckets + contract rates
        attendance_model = self.env.get("security.attendance.record")
        contract_model = self.env.get("security.client.contract")
        mtd_approved_billing = 0.0
        exception_count = 0
        pending_approval_count = 0

        if attendance_model:
            exception_count = attendance_model.search_count(
                [("has_billing_exception", "=", True)]
            )
            pending_approval_count = attendance_model.search_count(
                [("has_billing_exception", "=", True), ("billing_approved", "=", False)]
            )
            if contract_model:
                approved_recs = attendance_model.search([
                    ("shift_date", ">=", mtd_start),
                    ("shift_date", "<=", mtd_end),
                    ("status", "in", ("present", "late", "early_leave")),
                    "|",
                    ("has_billing_exception", "=", False),
                    "&",
                    ("has_billing_exception", "=", True),
                    ("billing_approved", "=", True),
                ])
                for rec in approved_recs:
                    mtd_approved_billing += rec.billing_amount or 0.0

        # Detect if payment-tracking module is active
        has_payments = "security.client.payment" in self.env

        # Invoice totals (MTD)
        mtd_invoices = self.search([
            ("invoice_date", ">=", str(mtd_start)),
            ("invoice_date", "<=", str(mtd_end)),
            ("state", "!=", "cancelled"),
        ])
        invoiced_mtd = sum(mtd_invoices.filtered(lambda i: i.state in ("sent", "paid")).mapped("total_amount"))
        
        if has_payments:
            # MTD Revenue Collected: sum of actual posted payments in the current month
            paid_mtd = sum(self.env["security.client.payment"].search([
                ("payment_date", ">=", str(mtd_start)),
                ("payment_date", "<=", str(mtd_end)),
                ("state", "=", "posted"),
            ]).mapped("amount"))
        else:
            paid_mtd = sum(mtd_invoices.filtered(lambda i: i.state == "paid").mapped("total_amount"))

        # All-time outstanding
        all_invoices = self.search([("state", "not in", ("cancelled",))])
        total_invoiced = sum(all_invoices.filtered(lambda i: i.state in ("sent", "paid")).mapped("total_amount"))
        
        if has_payments:
            active_invoices = all_invoices.filtered(lambda i: i.state in ("sent", "paid"))
            outstanding = sum(active_invoices.mapped("balance_amount"))
        else:
            total_paid = sum(all_invoices.filtered(lambda i: i.state == "paid").mapped("total_amount"))
            outstanding = max(total_invoiced - total_paid, 0.0)

        # Monthly revenue trend (last 6 months, invoiced)
        monthly_trend = []
        for i in range(5, -1, -1):
            ref = today.replace(day=1)
            if i > 0:
                # Go back i months
                year = ref.year
                month = ref.month - i
                while month <= 0:
                    month += 12
                    year -= 1
                ref = ref.replace(year=year, month=month)
            m_start = ref
            m_end = ref.replace(day=calendar.monthrange(ref.year, ref.month)[1])
            m_invoices = self.search([
                ("invoice_date", ">=", str(m_start)),
                ("invoice_date", "<=", str(m_end)),
                ("state", "in", ("sent", "paid")),
            ])
            
            if has_payments:
                m_payments = self.env["security.client.payment"].search([
                    ("payment_date", ">=", str(m_start)),
                    ("payment_date", "<=", str(m_end)),
                    ("state", "=", "posted"),
                ])
                trend_paid = sum(m_payments.mapped("amount"))
            else:
                trend_paid = sum(m_invoices.filtered(lambda i: i.state == "paid").mapped("total_amount"))

            monthly_trend.append({
                "month": m_start.strftime("%b %Y"),
                "amount": round(sum(m_invoices.mapped("total_amount")), 2),
                "paid": round(trend_paid, 2),
            })

        # Top clients by invoiced amount
        client_data = defaultdict(lambda: {"invoiced": 0.0, "paid": 0.0, "id": None})
        for inv in all_invoices:
            if inv.state not in ("sent", "paid"):
                continue
            cname = inv.partner_id.name or "Unknown"
            if not client_data[cname]["id"]:
                client_data[cname]["id"] = inv.partner_id.id
            client_data[cname]["invoiced"] += inv.total_amount
            if has_payments:
                client_data[cname]["paid"] += inv.paid_amount
            else:
                if inv.state == "paid":
                    client_data[cname]["paid"] += inv.total_amount

        top_clients = sorted(
            [
                {
                    "name": name,
                    "id": data["id"],
                    "invoiced": round(data["invoiced"], 2),
                    "paid": round(data["paid"], 2),
                    "outstanding": round(max(data["invoiced"] - data["paid"], 0.0), 2),
                }
                for name, data in client_data.items()
            ],
            key=lambda x: x["invoiced"],
            reverse=True,
        )[:8]

        return {
            "mtd_approved_billing": round(mtd_approved_billing, 2),
            "invoiced_mtd": round(invoiced_mtd, 2),
            "paid_mtd": round(paid_mtd, 2),
            "outstanding": round(outstanding, 2),
            "exception_count": exception_count,
            "pending_approval_count": pending_approval_count,
            "monthly_trend": monthly_trend,
            "top_clients": top_clients,
            "currency_symbol": self.env.company.currency_id.symbol or "N$",
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

    @api.onchange("site_id")
    def _onchange_site_id(self):
        for line in self:
            if line.site_id and line.post_id and line.post_id.site_id != line.site_id:
                line.post_id = False

    @api.onchange("post_id")
    def _onchange_post_id(self):
        for line in self:
            if line.post_id:
                if line.post_id.site_id and not line.site_id:
                    line.site_id = line.post_id.site_id

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
        invoiced_mtd = sum(mtd_invoices.filtered(lambda i: i.state in ("sent", "paid")).mapped("total_amount"))

        # Detect if payment-tracking module is active
        has_payments = "security.client.payment" in self.env

        if has_payments:
            collected_mtd = sum(self.env["security.client.payment"].search([
                ("payment_date", ">=", month_start),
                ("state", "=", "posted"),
            ]).mapped("amount"))
        else:
            collected_mtd = sum(
                mtd_invoices.filtered(lambda i: i.state == "paid").mapped("total_amount")
            )

        if has_payments:
            # For outstanding/overdue, we only care about invoices that are not cancelled or draft
            active_outstanding = Invoice.search([("state", "in", ["sent", "paid"])])
            outstanding_total = sum(active_outstanding.mapped("balance_amount"))
            overdue_total = sum(
                active_outstanding.filtered(
                    lambda i: i.due_date and i.due_date < today
                ).mapped("balance_amount")
            )
        else:
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
            is_overdue = False
            if last_inv and last_inv.due_date and last_inv.due_date < today:
                if has_payments:
                    is_overdue = bool(last_inv.balance_amount > 0.01)
                else:
                    is_overdue = bool(last_inv.state not in ("paid", "cancelled"))

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
                "is_overdue": is_overdue,
            })

        recent_data = []
        for i in Invoice.search(
            [("state", "not in", ["cancelled"])],
            order="invoice_date desc",
            limit=12,
        ):
            is_overdue = False
            if i.due_date and i.due_date < today:
                if has_payments:
                    is_overdue = bool(i.balance_amount > 0.01)
                else:
                    is_overdue = bool(i.state not in ("paid", "cancelled"))

            recent_data.append({
                "id": i.id,
                "name": i.name,
                "client": i.partner_id.name,
                "date": str(i.invoice_date) if i.invoice_date else "",
                "due": str(i.due_date) if i.due_date else "",
                "total": i.total_amount,
                "state": i.state,
                "overdue": is_overdue,
            })

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


class ResPartner(models.Model):
    _inherit = "res.partner"

    security_billing_plan_count = fields.Integer(
        compute="_compute_security_billing_counts",
        string="Billing Plans",
    )
    security_contract_count = fields.Integer(
        compute="_compute_security_billing_counts",
        string="Security Contracts",
    )
    security_invoice_count = fields.Integer(
        compute="_compute_security_billing_counts",
        string="Security Invoices",
    )

    def _compute_security_billing_counts(self):
        plan_model = self.env.get("security.billing.plan")
        contract_model = self.env.get("security.client.contract")
        invoice_model = self.env.get("security.billing.invoice")
        for partner in self:
            partner.security_billing_plan_count = (
                plan_model.search_count([("partner_id", "=", partner.id)]) if plan_model else 0
            )
            partner.security_contract_count = (
                contract_model.search_count([("partner_id", "=", partner.id)]) if contract_model else 0
            )
            partner.security_invoice_count = (
                invoice_model.search_count([("partner_id", "=", partner.id)]) if invoice_model else 0
            )

    def action_view_security_billing_plans(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("security_billing.action_security_billing_plan")
        action.update({
            "domain": [("partner_id", "=", self.id)],
            "context": {"default_partner_id": self.id},
        })
        return action

    def action_view_security_contracts(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("security_operations.action_security_client_contract")
        action.update({
            "domain": [("partner_id", "=", self.id)],
            "context": {"default_partner_id": self.id},
        })
        return action

    def action_view_security_invoices(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("security_billing.action_security_billing_invoice")
        action.update({
            "domain": [("partner_id", "=", self.id)],
            "context": {"default_partner_id": self.id},
        })
        return action

