{
    "name": "Security AI Engine",
    "summary": (
        "10-feature AI layer + global assistant: anomaly detection, risk profiling, "
        "billing audit, roster optimisation, shift fill, incident advisor, leave coverage, "
        "document renewal, performance review, payslip explanation, AI chat panel"
    ),
    "version": "19.0.4.0.0",
    "category": "Human Resources",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "depends": [
        "security_billing",
        "security_shift_planner",
        "security_attendance",
        "security_discipline",
        "security_leave",
        "security_documents",
        "security_payroll_core",
        "web",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/security_ai_config_views.xml",
        "views/security_ai_client_actions.xml",
        "views/security_ai_chat_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            # Component library + field widget (must load before chat panel)
            "security_ai_engine/static/src/js/ai_output_widget.js",
            "security_ai_engine/static/src/xml/ai_output_widget.xml",
            # Global AI chat panel (mounted via main_components registry)
            "security_ai_engine/static/src/css/ai_chat.css",
            "security_ai_engine/static/src/js/ai_chat_panel.js",
            "security_ai_engine/static/src/xml/ai_chat_panel.xml",
            # Admin dashboard
            "security_ai_engine/static/src/js/ai_admin_config.js",
            "security_ai_engine/static/src/xml/ai_admin_config.xml",
        ],
    },
    "installable": True,
    "application": False,
}
