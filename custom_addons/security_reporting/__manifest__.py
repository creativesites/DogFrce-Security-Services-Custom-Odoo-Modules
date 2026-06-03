{
    "name": "Security Reporting",
    "summary": "Operational, payroll, discipline, billing, and payment reporting dashboards",
    "version": "19.0.1.0.0",
    "category": "Reporting",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "depends": [
        "web",
        "security_accounting_controls",
        "security_discipline",
        "security_loans",
    ],
    "data": [
        "views/security_reporting_views.xml",
        "views/security_reporting_client_actions.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "security_reporting/static/src/css/executive_dashboard.css",
            "security_reporting/static/src/js/executive_dashboard.js",
            "security_reporting/static/src/xml/executive_dashboard.xml",
        ],
    },
    "installable": True,
    "application": False,
}
