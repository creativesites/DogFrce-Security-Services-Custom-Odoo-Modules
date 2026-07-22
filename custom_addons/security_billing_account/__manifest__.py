{
    "name": "Security Billing Invoicing Integration",
    "summary": "Tightly integrates custom security invoices with standard Odoo account.move Customer Invoices.",
    "version": "19.0.1.0.0",
    "category": "Security/Accounting",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "depends": ["security_billing", "account", "security_accounting_controls"],
    "data": [
        "views/security_billing_invoice_views.xml",
    ],
    "post_init_hook": "_auto_reconcile_existing_invoices",
    "auto_install": True,
    "installable": True,
}

