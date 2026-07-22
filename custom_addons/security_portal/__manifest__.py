{
    "name": "Security Client Portal Dashboard",
    "summary": "Secure web controllers and premium Odoo client portals under /my/security-dashboard offering real-time posting statistics, active rosters, and feedback reviews.",
    "version": "19.0.1.0.0",
    "category": "Security/Portal",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "depends": ["portal", "security_operations", "security_attendance", "security_base"],
    "data": [
        "views/security_portal_templates.xml",
        "views/security_portal_views.xml",
    ],
    "auto_install": True,
    "installable": True,
}
