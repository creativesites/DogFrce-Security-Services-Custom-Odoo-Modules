{
    "name": "Security Localization Namibia",
    "summary": "Namibia-specific payroll, holiday, and invoice configuration",
    "version": "19.0.1.0.0",
    "category": "Localization",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "depends": ["security_leave", "security_operations"],
    "data": [
        "security/ir.model.access.csv",
        "data/security_l10n_na_data.xml",
        "views/security_l10n_na_views.xml",
        "reports/security_paye_report.xml",
        "reports/security_ssc_report.xml",
    ],
    "installable": True,
    "application": False,
}
