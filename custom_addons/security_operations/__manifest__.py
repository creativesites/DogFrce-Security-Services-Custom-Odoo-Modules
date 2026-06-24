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
        "data/security_operations_cron.xml",
        "views/security_operations_menu.xml",
        "views/security_roster_wizard_views.xml",
        "views/security_operations_views.xml",
        "views/security_client_contract_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "security_operations/static/src/css/site_hub.css",
            "security_operations/static/src/xml/site_hub.xml",
            "security_operations/static/src/js/site_hub.js",
        ],
    },
    "installable": True,
    "application": False,
}
