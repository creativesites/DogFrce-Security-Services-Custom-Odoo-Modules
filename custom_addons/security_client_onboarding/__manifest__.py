{
    "name": "Security Client Onboarding",
    "summary": "Five-step wizard to onboard a new security client: sites, shift requirements, billing plan, and first roster batch",
    "version": "19.0.1.0.0",
    "category": "Human Resources",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "depends": ["security_operations", "security_billing"],
    "data": [
        "security/ir.model.access.csv",
        "views/security_client_onboarding_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "security_client_onboarding/static/src/css/onboarding_wizard.css",
        ],
    },
    "installable": True,
    "application": False,
}
