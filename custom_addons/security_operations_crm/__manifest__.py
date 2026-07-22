{
    "name": "Security Operations CRM Intelligence Bridge",
    "summary": "Synchronizes real-time security operational performance metrics (compliance, incidents, breaches) directly to CRM opportunities.",
    "version": "19.0.1.0.0",
    "category": "Security/CRM",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "depends": ["security_operations", "crm", "security_base"],
    "data": [
        "views/crm_lead_views.xml",
    ],
    "auto_install": True,
    "installable": True,
}
