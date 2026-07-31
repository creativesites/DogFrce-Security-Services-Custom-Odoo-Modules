{
    "name": "DogForce Zambia Demo Site Suite",
    "version": "19.0.1.0.0",
    "category": "Security/Demo",
    "summary": "Master meta-module for Sentinel Security Services Zambia Demo Site on Alibaba Cloud Server.",
    "description": """
        DogForce Security Services — Alibaba Cloud Zambia Demo Site Suite:
        - Meta-installer that aggregates all active Zambian security modules.
        - Includes security_suite, security_l10n_zm, security_zra_invoice, security_demo_data_zm,
          security_demo_site, security_shift_planner, and security_ai_whatsapp_bridge.
        - Used for single-command database updates on demo instances (zambia-demo & dogforce_dev).
        - EXCLUDED from Namibia Production deployments (199.192.23.46).
    """,
    "author": "Google DeepMind team working on Advanced Agentic Coding",
    "license": "LGPL-3",
    "depends": [
        "security_suite",
        "security_l10n_zm",
        "security_zra_invoice",
        "security_demo_data_zm",
        "security_demo_site",
        "security_shift_planner",
        "security_ai_whatsapp_bridge",
    ],
    "data": [],
    "assets": {},
    "installable": True,
    "application": True,
    "auto_install": False,
}
