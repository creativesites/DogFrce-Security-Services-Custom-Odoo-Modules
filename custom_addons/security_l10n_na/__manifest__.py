{
    "name": "Security Localization Namibia",
    "summary": "Namibia-specific payroll, holiday, and invoice configuration",
    "version": "19.0.1.0.0",
    "category": "Localization",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "depends": ["security_leave"],
    "data": [
        "security/ir.model.access.csv",
        "data/security_l10n_na_data.xml",
        "views/security_l10n_na_views.xml",
    ],
    "installable": True,
    "application": False,
}
