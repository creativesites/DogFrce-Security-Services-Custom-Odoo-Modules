{
    "name": "Security Notifications",
    "summary": "Internal alert and notification system for security operations",
    "version": "19.0.1.0.0",
    "category": "Security",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "depends": ["security_documents", "security_leave", "security_billing", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "data/security_notifications_cron.xml",
        "views/security_notifications_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "security_notifications/static/src/js/notification_bell.js",
            "security_notifications/static/src/xml/notification_bell.xml",
        ],
    },
    "installable": True,
    "application": False,
}
