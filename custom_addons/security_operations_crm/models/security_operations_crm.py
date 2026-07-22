import logging
from datetime import date, timedelta
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = "crm.lead"

    opportunity_health = fields.Selection(
        [
            ("1", "Critical Risk"),
            ("2", "At Risk"),
            ("3", "Moderate"),
            ("4", "Good"),
            ("5", "Excellent Health"),
        ],
        string="Operational Opportunity Health",
        default="5",
        help="Real-time performance rating calculated from attendance compliance, incidents, and billing.",
    )
    renewal_probability = fields.Float(
        string="Renewal Probability (%)",
        default=100.0,
        help="Computed possibility of contract renewal based on service SLA adherence.",
    )
    account_risk = fields.Selection(
        [
            ("low", "Low Risk"),
            ("medium", "Medium Risk"),
            ("high", "High Operational Risk"),
        ],
        string="Account Operational Risk",
        default="low",
    )
    sla_breach_count = fields.Integer(
        string="SLA Breach Count (MTD)",
        default=0,
        help="Total missed posts or AWOL occurrences in the trailing 30 days.",
    )

    def recalculate_operational_health(self):
        """
        Gathers trailing 30-day site compliance metrics, overdue invoices, and incidents,
        and computes dynamic rating, renewal probability, and risk tiers.
        """
        today = date.today()
        cutoff_30_days = today - timedelta(days=30)
        cutoff_15_days = today - timedelta(days=15)

        for lead in self:
            partner = lead.partner_id
            if not partner:
                lead.write({
                    "opportunity_health": "5",
                    "renewal_probability": 100.0,
                    "account_risk": "low",
                    "sla_breach_count": 0,
                })
                continue

            # 1. Count trailing 30-day SLA breaches (AWOL / No Show)
            attendance_model = self.env.get("security.attendance.record")
            unexcused_absences = 0
            if attendance_model:
                unexcused_absences = attendance_model.search_count([
                    ("partner_id", "=", partner.id),
                    ("shift_date", ">=", str(cutoff_30_days)),
                    ("manual_presence", "in", ["absent", "awol"]),
                ])

            # 2. Count trailing 30-day critical incidents
            incident_model = self.env.get("security.incident")
            critical_incidents = 0
            if incident_model:
                critical_incidents = incident_model.search_count([
                    ("site_id.partner_id", "=", partner.id),
                    ("create_date", ">=", str(cutoff_30_days)),
                    ("severity", "=", "critical"),
                ])

            # 3. Count overdue unpaid invoices > 15 days past due
            invoice_model = self.env.get("security.billing.invoice")
            overdue_invoices = 0
            if invoice_model:
                overdue_invoices = invoice_model.search_count([
                    ("partner_id", "=", partner.id),
                    ("state", "not in", ["paid", "cancelled"]),
                    ("due_date", "<", str(cutoff_15_days)),
                ])

            # 4. Score Calculation (Base 100 Points)
            score = 100.0
            score -= (unexcused_absences * 5.0)
            score -= (overdue_invoices * 10.0)
            score -= (critical_incidents * 15.0)

            # Bound score to [0, 100]
            score = max(0.0, min(100.0, score))

            # Map score to fields
            if score >= 90.0:
                health = "5"
                risk = "low"
            elif score >= 75.0:
                health = "4"
                risk = "low"
            elif score >= 60.0:
                health = "3"
                risk = "medium"
            elif score >= 45.0:
                health = "2"
                risk = "high"
            else:
                health = "1"
                risk = "high"

            lead.write({
                "opportunity_health": health,
                "renewal_probability": score,
                "account_risk": risk,
                "sla_breach_count": unexcused_absences,
            })

            # 5. Automatically create a Customer Success Activity if risk rises to HIGH
            if risk == "high":
                lead._create_customer_success_activity()

    def _create_customer_success_activity(self):
        """Creates a high-priority customer success task activity on the opportunity."""
        self.ensure_one()
        activity_type = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        if not activity_type:
            return

        # Check if we already have an active Customer Success Review activity to avoid duplicates
        existing = self.env["mail.activity"].search_count([
            ("res_model", "=", "crm.lead"),
            ("res_id", "=", self.id),
            ("summary", "=", "Customer Success Review — Operational SLA Breach"),
        ])
        if not existing:
            self.env["mail.activity"].create({
                "res_model_id": self.env["ir.model"]._get("crm.lead").id,
                "res_id": self.id,
                "activity_type_id": activity_type.id,
                "summary": "Customer Success Review — Operational SLA Breach",
                "note": _(
                    "This account has breached multiple operational SLAs (MTD SLA Breaches: %s). "
                    "Please execute an immediate success review meeting with the client team."
                ) % self.sla_breach_count,
                "date_deadline": date.today() + timedelta(days=3),
                "user_id": self.user_id.id or self.env.user.id,
            })


class SecurityOperationsCrmBridge(models.AbstractModel):
    _name = "security.operations.crm.bridge"
    _description = "Security Operations CRM Event Bridge"

    @api.model
    def _handle_bus_event(self, event_name, source_model, source_id, payload):
        """
        Receives operational notifications from the central DeployGuard Intelligence Bus
        and instantly recalculates CRM opportunities matching the client record.
        """
        _logger.info("CRM Bridge | Processing operational event: %s", event_name)

        partner_id = False
        if event_name in ["attendance.missed", "attendance.late"]:
            if source_model == "security.attendance.record":
                record = self.env["security.attendance.record"].browse(source_id)
                if record.exists() and record.partner_id:
                    partner_id = record.partner_id.id

        elif event_name == "incident.logged":
            if source_model == "security.incident":
                record = self.env["security.incident"].browse(source_id)
                if record.exists() and record.site_id and record.site_id.partner_id:
                    partner_id = record.site_id.partner_id.id

        if partner_id:
            # Recalculate any active/unclosed opportunities for this client partner
            leads = self.env["crm.lead"].search([
                ("partner_id", "=", partner_id),
                ("active", "=", True),
                ("probability", "<", 100.0),
            ])
            if leads:
                _logger.info("CRM Bridge | Triggering operational score recalculation for %s active leads of partner_id=%s", len(leads), partner_id)
                leads.recalculate_operational_health()
