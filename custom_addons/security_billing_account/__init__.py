from . import models


def _auto_reconcile_existing_invoices(env):
    """Post-init hook to automatically reconcile existing invoices on activation."""
    invoices = env["security.billing.invoice"].search([])
    if invoices:
        # Wrap in try/except to avoid blocking module installation if some data is corrupt
        try:
            invoices.action_auto_reconcile()
        except Exception:
            pass
