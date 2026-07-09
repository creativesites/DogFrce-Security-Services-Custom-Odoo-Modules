{
    "name": "Security Client Onboarding",
    "summary": "6-step wizard to onboard a new security client: contract, sites, shift requirements, billing plan, and first roster batch",
    "version": "19.0.1.0.0",
    "category": "Human Resources",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "depends": ["security_operations", "security_billing"],
    "data": [
        "security/ir.model.access.csv",
        "views/security_client_onboarding_views.xml",
    ],
    "installable": True,
    "application": False,
}
