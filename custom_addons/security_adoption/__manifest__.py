{
    "name": "DogForce Adoption Engine",
    "summary": "Measures expected operational work actually executed through the system -- not login counts",
    "description": """
        docs/deployguard/09-adoption-engine.md, Phase 5. Built ahead of the
        spec's own gate ("do not start 5.2 onwards until the privacy/legal
        review and the employment-contract notice exist") on explicit
        product-owner instruction accepting that risk -- see
        BUILD-STATUS-AND-PHASE-PLAN.md Phase 5 decisions section.

        What this is: a fairness-first measurement layer over five MVP
        workflow_keys (attendance.post, incident.review, site.visit,
        training.mandatory, shift.handover), each grounded in a real,
        already-existing model in this repo rather than a Platform event
        the DeployGuard Platform (which doesn't exist yet, Track A) would
        emit:

        | workflow_key        | Source of truth                                              |
        |----------------------|--------------------------------------------------------------|
        | attendance.post      | security.attendance.batch reaching reviewed/locked            |
        | site.visit            | security.work.task (checklist code site.visit) submitted/verified |
        | shift.handover        | security.work.task (checklist code shift.handover) submitted/verified |
        | incident.review       | security.incident reaching approved within its 24h SLA        |
        | training.mandatory    | security.training.assignment reaching completed by due_date   |

        Expected-work materialisation runs for the day/week that has just
        closed (T-1), not forward for days that haven't happened yet --
        predicting who is on duty tomorrow is exactly the shift-based
        assignment problem security_work's own schedule-rule model
        explicitly declines to guess at (see that model's docstring), so
        this module doesn't invent a second, worse guess.

        Known, documented gaps (not fabricated, not silently skipped):
        - incident.review has no "assigned reviewer" field on
          security.incident. Expected ownership falls back to the first
          active security_base.group_security_manager member until the
          incident is actually approved, at which point the item is
          re-attributed to the real approver. This is an approximation,
          called out here rather than invented as a fake field.
        - system_fault excusal (support-ticket-linked retroactive excusal)
          is not implemented -- there is no support-ticket model in this
          repo to link it to yet.
        - Desktop UI (own-score view, explanation screen, adoption
          overview -- spec's Desktop 5.7) is NOT built in this slice. The
          scoring and materialisation backend is real and tested; the
          desktop screens are tracked as a separate, explicitly deferred
          follow-up in BUILD-STATUS-AND-PHASE-PLAN.md.
        - The ASSIST check-in is a plain record (question + one of the 8
          spec answers + routed action), not a chat-style UI -- consistent
          with this repo's pattern of building real backend routing logic
          first and flagging interactive UI as a following slice.
    """,
    "version": "19.0.1.0.0",
    "category": "Security/Operations",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "depends": [
        "mail", "security_base", "security_operations", "security_attendance",
        "security_work", "security_training", "security_leave", "security_discipline",
    ],
    "data": [
        "security/security_groups.xml",
        "security/ir.model.access.csv",
        "security/security_adoption_rules.xml",
        "data/security_adoption_definitions.xml",
        "data/security_adoption_cron.xml",
        "views/security_adoption_views.xml",
        "views/security_adoption_menu.xml",
    ],
    "installable": True,
    "application": False,
}
