import logging

from odoo import fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SecurityZraBulkSubmit(models.TransientModel):
    _name = "security.zra.bulk.submit"
    _description = "ZRA Bulk Invoice Submit Wizard"

    invoice_ids = fields.Many2many(
        "security.billing.invoice",
        "security_zra_bulk_submit_invoice_rel",
        "wizard_id",
        "invoice_id",
        string="Invoices to Submit",
        domain="[('zra_state', '!=', 'accepted'), ('state', 'not in', ['cancelled'])]",
    )
    result_log = fields.Text(string="Submission Results", readonly=True)

    def action_submit_all(self):
        self.ensure_one()
        if not self.invoice_ids:
            raise UserError(
                "No invoices selected. Please select at least one invoice to submit to ZRA."
            )
        results = []
        for inv in self.invoice_ids:
            try:
                inv._submit_to_zra()
                results.append(f"✓ {inv.name} — accepted")
            except Exception as exc:
                results.append(f"✗ {inv.name} — {exc}")
                _logger.warning("Bulk ZRA submission failed for %s: %s", inv.name, exc)
        self.result_log = "\n".join(results)
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
