{
    "name": "DeployGuard Support & Owner Overview",
    "summary": "In-app problem reports, task feedback, contextual help and an evidence-backed owner overview",
    "description": """
        Rebuilt 2026-09-28 (desktop/RECONCILIATION.md §D-23): the desktop
        called these models and BUILD-STATUS marked them done, but no source
        had ever been committed. The API matches what desktop/src/api/support.ts
        calls.

        - security.support.request: "Report a problem" from the desktop,
          with sanitised diagnostics. A request flagged as a system fault is
          what security_adoption's system_fault excusal refers to.
        - security.task.feedback: the one-tap "how was that?" after a task.
          A training and usability signal, not a performance score.
        - security.help.article.get_contextual_articles: help for the screen
          the employee is on.
        - security.owner.digest.get_owner_overview: company-wide tiles where
          every number carries the domain of the records behind it.
    """,
    "version": "19.0.1.0.0",
    "category": "Security/Operations",
    "author": "DogForce Security Services",
    "license": "LGPL-3",
    "depends": ["security_base", "security_work", "security_help", "mail"],
    "data": [
        "security/security_support_security.xml",
        "security/ir.model.access.csv",
        "data/security_support_sequence.xml",
        "views/security_support_views.xml",
    ],
    "installable": True,
    "application": False,
}
