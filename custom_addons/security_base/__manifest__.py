{
    "name": "Security Base",
    "summary": "Core security company master data and guard profiles",
    "version": "19.0.1.0.0",
    "category": "Human Resources",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "depends": ["hr", "mail"],
    "data": [
        "security/security_groups.xml",
        "security/ir.model.access.csv",
        "views/security_base_menu.xml",
        "views/security_base_views.xml",
        "views/hr_employee_views.xml",
    ],
    "installable": True,
    "application": False,
}
