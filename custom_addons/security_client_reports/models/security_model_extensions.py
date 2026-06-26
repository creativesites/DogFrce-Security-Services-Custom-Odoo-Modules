"""
Lightweight model extensions that add Export wizard launchers to existing models.
"""
from odoo import models


class SecurityRosterBatchExport(models.Model):
    _inherit = "security.roster.batch"

    def action_open_roster_export_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Export Roster to Excel",
            "res_model": "security.roster.export.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_batch_id": self.id},
        }


class SecurityBillingInvoiceExport(models.Model):
    _inherit = "security.billing.invoice"

    def action_open_billing_export_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Export Billing to Excel",
            "res_model": "security.billing.export.wizard",
            "view_mode": "form",
            "target": "new",
        }
