{
    "name": "Security Billing CRM Integration",
    "summary": "Tightly integrates DeployGuard security billing plans with standard Odoo CRM leads and opportunities.",
    "version": "19.0.1.0.0",
    "category": "Security/CRM",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "depends": ["security_billing", "crm"],
    "data": [
        "views/crm_lead_views.xml",
    ],
    "auto_install": True,
    "installable": True,
}
