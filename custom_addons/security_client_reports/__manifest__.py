{
    "name": "Security Client Reports",
    "summary": "Client attendance and service reports for security contracts",
    "version": "19.0.1.0.0",
    "category": "Reporting",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "depends": ["security_billing", "security_reporting", "security_operations", "security_attendance"],
    "data": [
        "security/ir.model.access.csv",
        "views/security_client_reports_views.xml",
        "views/security_export_wizard_views.xml",
        "views/security_report_buttons.xml",
        "reports/security_client_service_report.xml",
        "reports/security_roster_report.xml",
    ],
    "installable": True,
    "application": False,
}
