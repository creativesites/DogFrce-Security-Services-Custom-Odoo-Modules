from . import models


def _auto_reconcile_existing_invoices(cr, registry):
    """Post-init hook to automatically reconcile existing invoices on activation."""
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    invoices = env["security.billing.invoice"].search([])
    if invoices:
        # Wrap in try/except to avoid blocking module installation if some data is corrupt
        try:
            invoices.action_auto_reconcile()
        except Exception:
            pass
