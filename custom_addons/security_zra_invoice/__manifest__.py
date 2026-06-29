{
    "name": "Security ZRA Smart Invoice",
    "summary": "ZRA Smart Invoice (VSDC) integration for DogForce billing — Zambia e-invoicing mandate",
    "version": "19.0.1.0.0",
    "category": "Localization",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "depends": ["security_billing", "security_operations"],
    "data": [
        "security/ir.model.access.csv",
        "data/security_zra_cron.xml",
        "views/security_zra_views.xml",
        "views/security_zra_bulk_wizard_views.xml",
        "reports/security_zra_invoice_report.xml",
    ],
    "installable": True,
    "application": False,
}
