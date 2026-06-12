{
    "name": "DogForce Help Centre",
    "version": "19.0.1.0.0",
    "summary": "Built-in help, user guides, and how-to articles for the DogForce platform",
    "category": "Security/Help",
    "author": "DogForce Security Services",
    "depends": ["web", "security_base"],
    "data": [
        "security/ir.model.access.csv",
        "security/security_help_security.xml",
        "views/help_views.xml",
        "data/help_content.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "security_help/static/src/css/help_portal.css",
            "security_help/static/src/xml/help_portal.xml",
            "security_help/static/src/js/help_portal.js",
        ],
    },
    "application": False,
    "installable": True,
    "auto_install": False,
}
