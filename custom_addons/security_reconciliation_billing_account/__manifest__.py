{
    "name": "Security Reconciliation — Billing & Accounting",
    "summary": "Reconciles DeployGuard invoices, payments, and credit notes with Odoo Accounting using Reconciliation Core.",
    "version": "19.0.1.0.0",
    "category": "Security/Accounting",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "depends": [
        "security_reconciliation_core",
        "security_billing",
        "account",
        "security_accounting_controls",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/security_reconciliation_billing_data.xml",
        "views/security_reconciliation_billing_views.xml",
    ],
    "auto_install": True,
    "installable": True,
}
