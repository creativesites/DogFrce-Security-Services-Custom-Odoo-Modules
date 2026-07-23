{
    "name": "Security AI WhatsApp Bridge",
    "summary": "Conversational AI WhatsApp webhook integrations linking instant messaging streams with roster matching, AWOL logging, and supervisor incident generation.",
    "version": "19.0.1.0.0",
    "category": "Security/AI",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "depends": ["security_operations", "security_attendance", "security_base", "security_ai_engine"],
    "data": [
        "security/ir.model.access.csv",
        "views/security_whatsapp_config_views.xml",
        "views/security_whatsapp_message_log_views.xml",
    ],
    "auto_install": True,
    "installable": True,
}
