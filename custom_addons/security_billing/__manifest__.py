{
    "name": "Security Billing",
    "summary": "Security company client contracts, billing plans, and invoice generation",
    "version": "19.0.1.0.0",
    "category": "Accounting",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "depends": ["security_payroll_core"],
    "data": [
        "data/ir_sequence.xml",
        "data/security_billing_cron.xml",
        "security/ir.model.access.csv",
        "views/security_billing_views.xml",
        "views/security_billing_wizard_views.xml",
        "reports/security_invoice_report.xml",
        "reports/security_invoice_aging_report.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "security_billing/static/src/js/billing_dashboard.js",
            "security_billing/static/src/xml/billing_dashboard.xml",
        ],
    },
    "installable": True,
    "application": False,
}
