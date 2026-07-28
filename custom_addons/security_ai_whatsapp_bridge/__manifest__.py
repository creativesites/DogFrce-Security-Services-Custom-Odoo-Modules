{
    "name": "Security AI WhatsApp Bridge",
    "summary": "Conversational AI WhatsApp webhook integrations linking instant messaging streams with roster matching, AWOL logging, and supervisor incident generation.",
    "version": "19.0.1.0.0",
    "category": "Security/AI",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "depends": ["hr", "security_operations", "security_attendance", "security_base", "security_ai_engine"],
    "data": [
        "security/ir.model.access.csv",
        "views/security_whatsapp_whitelist_views.xml",
        "views/security_whatsapp_config_views.xml",
        "views/security_whatsapp_message_log_views.xml",
        "views/menu_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "security_ai_whatsapp_bridge/static/src/css/whatsapp_dashboard.css",
            "security_ai_whatsapp_bridge/static/src/xml/whatsapp_dashboard.xml",
            "security_ai_whatsapp_bridge/static/src/js/whatsapp_dashboard.js",
            "security_ai_whatsapp_bridge/static/src/js/whatsapp_chat_workspace.js",
        ],
    },
    "auto_install": True,
    "installable": True,
}
