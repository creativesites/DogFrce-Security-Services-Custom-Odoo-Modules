{
    "name": "DeployGuard Guided Tasks",
    "summary": "Teach while doing: state-aware guidance through real ERP workflows",
    "description": """
        Guided tasks for DeployGuard (docs/deployguard/dogforce-roles-and-pipeline.md,
        V2 brief sections 11-17).

        A guidance *flow* is data: steps, each with where it happens, what to
        highlight, why it matters, help, and how DeployGuard knows it's done
        (the ERP's UI state and/or a server check against real records).

        A guidance *session* is one employee working through one flow,
        usually for one real task. The server decides which step to show from
        what the employee is actually doing, never from "step 3 comes after
        step 2", and records operational evidence events (step shown, done,
        deviation, help requested). It records nothing about mouse, keyboard
        or time on screen.

        The guidance runner is an ordinary Odoo web asset. It reports which
        screen the employee is on and highlights the real control. It never
        clicks or types. The DeployGuard desktop shows the same session in a
        side panel through Odoo's normal API, so nothing is ever injected into
        the ERP by the desktop (desktop/RECONCILIATION.md, C-10).

        AI (Gemini via security_ai_engine, if installed) can explain the
        current step. It only rephrases approved step content, is labelled as
        AI, and never advances or completes anything.
    """,
    "version": "19.0.1.0.0",
    "category": "Security/Operations",
    "author": "DogForce Security Services",
    "license": "LGPL-3",
    "depends": ["web", "mail", "security_base", "security_work"],
    "data": [
        "security/ir.model.access.csv",
        "security/security_guidance_security.xml",
        "views/guidance_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "security_guidance/static/src/css/guidance.css",
            "security_guidance/static/src/xml/guidance_overlay.xml",
            "security_guidance/static/src/js/anchors.js",
            "security_guidance/static/src/js/guidance_service.js",
        ],
    },
    "installable": True,
    "application": False,
}
