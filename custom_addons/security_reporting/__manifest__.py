{
    "name": "Security Reporting",
    "summary": "Operational, payroll, discipline, billing, and payment reporting dashboards",
    "version": "19.0.1.0.0",
    "category": "Reporting",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "depends": [
        "security_accounting_controls",
        "security_discipline",
        "security_loans",
    ],
    "data": [
        "views/security_reporting_views.xml",
    ],
    "installable": True,
    "application": False,
}
