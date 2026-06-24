from odoo import api, fields, models
from odoo.exceptions import UserError


class SecurityNotification(models.Model):
    _name = "security.notification"
    _description = "Security Platform Notification"
    _order = "create_date desc"
    _rec_name = "title"

    title = fields.Char(required=True)
    body = fields.Text()
    notification_type = fields.Selection([
        ("document_expiry", "Document Expiry"),
        ("invoice_overdue", "Invoice Overdue"),
        ("awol_alert", "AWOL Alert"),
        ("roster_gap", "Roster Gap"),
        ("system", "System"),
    ], default="system", required=True)
    severity = fields.Selection([
        ("info", "Info"),
        ("warning", "Warning"),
        ("critical", "Critical"),
    ], default="info", required=True)
    recipient_ids = fields.Many2many("res.users", string="Recipients")
    state = fields.Selection([
        ("unread", "Unread"),
        ("read", "Read"),
        ("dismissed", "Dismissed"),
    ], default="unread")
    related_model = fields.Char(string="Related Model")
    related_id = fields.Integer(string="Related Record ID")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.severity == "critical" and record.recipient_ids:
                record._send_email_notification()
        return records

    def _send_email_notification(self):
        self.ensure_one()
        for user in self.recipient_ids:
            if not user.email:
                continue
            self.env["mail.mail"].sudo().create({
                "subject": f"[DogForce Alert] {self.title}",
                "email_to": user.email,
                "body_html": f"""
                    <div style="font-family:Arial,sans-serif;padding:20px;max-width:600px;">
                        <div style="background:#dc2626;color:white;padding:12px 16px;border-radius:8px 8px 0 0;">
                            <strong>&#x1F6A8; Critical Alert — DogForce Security Suite</strong>
                        </div>
                        <div style="border:1px solid #e2e8f0;border-top:none;padding:16px;border-radius:0 0 8px 8px;">
                            <h3 style="margin:0 0 8px;color:#1e293b;">{self.title}</h3>
                            <p style="color:#475569;margin:0;">{self.body or ''}</p>
                            <hr style="border:none;border-top:1px solid #e2e8f0;margin:16px 0;"/>
                            <p style="font-size:12px;color:#94a3b8;margin:0;">
                                This is an automated alert from DogForce Security Suite.<br/>
                                Log in at <a href="http://localhost:8069">http://localhost:8069</a> to view details.
                            </p>
                        </div>
                    </div>
                """,
            }).send()

    def action_mark_read(self):
        self.state = "read"

    def action_dismiss(self):
        self.state = "dismissed"

    @api.model
    def action_scan_document_expiry(self):
        """Cron: create notifications for documents expiring within 30 days."""
        from datetime import date, timedelta
        cutoff = date.today() + timedelta(days=30)
        doc_model = self.env.get("security.employee.document")
        if not doc_model:
            return
        expiring = doc_model.search([
            ("expiry_date", "<=", str(cutoff)),
            ("expiry_date", ">=", str(date.today())),
            ("state", "!=", "expired"),
        ])
        hr_users = self.env["res.users"].search([
            ("group_ids", "in", [self.env.ref("base.group_user").id])
        ])
        for doc in expiring:
            existing = self.search([
                ("notification_type", "=", "document_expiry"),
                ("related_model", "=", "security.employee.document"),
                ("related_id", "=", doc.id),
                ("state", "!=", "dismissed"),
            ], limit=1)
            if not existing:
                self.create({
                    "title": f"Document Expiring: {doc.document_type_id.name if hasattr(doc, 'document_type_id') else 'Document'} — {doc.employee_id.name}",
                    "body": f"Document expires on {doc.expiry_date}. Please renew before this date.",
                    "notification_type": "document_expiry",
                    "severity": "warning" if (doc.expiry_date - date.today()).days > 14 else "critical",
                    "recipient_ids": [(6, 0, hr_users[:3].ids)],
                    "related_model": "security.employee.document",
                    "related_id": doc.id,
                })

    @api.model
    def action_scan_overdue_invoices(self):
        """Cron: create notifications for overdue invoices."""
        from datetime import date
        today = date.today()
        overdue = self.env["security.billing.invoice"].search([
            ("state", "not in", ["paid", "cancelled"]),
            ("due_date", "<", str(today)),
        ])
        manager_users = self.env["res.users"].search([
            ("group_ids", "in", [self.env.ref("base.group_system").id])
        ])
        for inv in overdue:
            existing = self.search([
                ("notification_type", "=", "invoice_overdue"),
                ("related_model", "=", "security.billing.invoice"),
                ("related_id", "=", inv.id),
                ("state", "!=", "dismissed"),
            ], limit=1)
            if not existing:
                self.create({
                    "title": f"Invoice Overdue: {inv.name} — {inv.partner_id.name if inv.partner_id else 'Unknown'}",
                    "body": f"Invoice {inv.name} was due on {inv.due_date}. Total: {inv.total_amount}.",
                    "notification_type": "invoice_overdue",
                    "severity": "critical",
                    "recipient_ids": [(6, 0, manager_users[:3].ids)],
                    "related_model": "security.billing.invoice",
                    "related_id": inv.id,
                })

    @api.model
    def action_scan_roster_gaps(self):
        """Cron (every 10 min): alert on unassigned slots starting within 2 h and missing check-ins."""
        from datetime import datetime, timedelta, time as _time
        now_utc = datetime.utcnow()
        gap_window_end = now_utc + timedelta(hours=2)
        today = fields.Date.context_today(self)

        slot_model = self.env.get("security.roster.slot")
        if slot_model:
            unassigned = slot_model.search([
                ("shift_date", "=", today),
                ("employee_id", "=", False),
                ("state", "not in", ["cancelled"]),
            ])
            for slot in unassigned:
                tmpl = slot.shift_template_id
                if not tmpl:
                    continue
                h = int(tmpl.start_hour)
                m = int(round((tmpl.start_hour - h) * 60))
                slot_start = datetime.combine(today, _time(h, m))
                if not (now_utc <= slot_start <= gap_window_end):
                    continue
                existing = self.search([
                    ("notification_type", "=", "roster_gap"),
                    ("related_model", "=", "security.roster.slot"),
                    ("related_id", "=", slot.id),
                    ("state", "!=", "dismissed"),
                ], limit=1)
                if not existing:
                    site_name = slot.site_id.name if slot.site_id else "Unknown Site"
                    self.create({
                        "title": f"Unassigned Slot: {site_name}",
                        "body": (
                            f"Slot at {site_name} (post: {slot.post_id.name if slot.post_id else 'N/A'}, "
                            f"shift: {tmpl.name}) starts within 2 hours with no guard assigned."
                        ),
                        "notification_type": "roster_gap",
                        "severity": "critical",
                        "related_model": "security.roster.slot",
                        "related_id": slot.id,
                    })

        record_model = self.env.get("security.attendance.record")
        if record_model:
            cutoff_str = fields.Datetime.to_string(now_utc - timedelta(minutes=15))
            late_records = record_model.search([
                ("shift_date", "=", today),
                ("check_in", "=", False),
                ("manual_presence", "not in", ["absent", "awol"]),
                ("scheduled_start", "!=", False),
                ("scheduled_start", "<=", cutoff_str),
            ])
            for rec in late_records:
                existing = self.search([
                    ("notification_type", "=", "roster_gap"),
                    ("related_model", "=", "security.attendance.record"),
                    ("related_id", "=", rec.id),
                    ("state", "!=", "dismissed"),
                ], limit=1)
                if not existing:
                    self.create({
                        "title": f"Missing Check-in: {rec.employee_id.name or 'Guard'}",
                        "body": (
                            f"{rec.employee_id.name or 'Guard'} at "
                            f"{rec.site_id.name or 'unknown site'} was scheduled "
                            f"but has not checked in."
                        ),
                        "notification_type": "roster_gap",
                        "severity": "warning",
                        "related_model": "security.attendance.record",
                        "related_id": rec.id,
                    })
