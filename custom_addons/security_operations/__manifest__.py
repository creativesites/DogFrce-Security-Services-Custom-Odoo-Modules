{
    "name": "Security Operations",
    "summary": "Security posts, site requirements, shift templates, and roster slots",
    "version": "19.0.1.0.0",
    "category": "Human Resources",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "depends": ["security_base", "contacts"],
    "data": [
        "security/ir.model.access.csv",
        "views/security_operations_menu.xml",
        "views/security_roster_wizard_views.xml",
        "views/security_operations_views.xml",
    ],
    "installable": True,
    "application": False,
}
