{
    "name": "DogForce Work Management",
    "summary": "Generic task and checklist primitives: assign, run, submit, verify",
    "description": """
        DeployGuard Work Management (BUILD-ORDER P4, cut down to what's
        buildable without the platform backend/worker — see
        docs/deployguard/08-work-management.md §1 for the full primitive
        set this is a slice of):
        - security.work.task: assignee, due date, state machine
          (open -> in_progress -> submitted -> verified, with
          could_not_complete and rejected/cancelled side paths).
        - security.work.checklist.template / .item.def: reusable
          checklist definitions (typed items: boolean/text/number/photo).
        - security.work.checklist.response: per-task answers to a
          template's items.
        Deliberately NOT here yet: ScheduleRule-based recurrence
        (materialising tasks from shift/site events), AutoCompleteRule
        (auto-closing tasks from Odoo events like attendance posting),
        and offline sync — those need the worker/API layer described in
        08-work-management.md §3-4 and BUILD-ORDER.md P4, which doesn't
        exist yet. Tasks here are created manually or by other addons
        calling this model directly; that's an honest MVP boundary, not
        an oversight.
    """,
    "version": "19.0.1.0.0",
    "category": "Security/Operations",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "depends": ["security_base", "security_operations", "mail"],
    "data": [
        "security/security_groups.xml",
        "security/ir.model.access.csv",
        "views/security_work_task_views.xml",
        "views/security_work_checklist_views.xml",
        "views/security_work_menu.xml",
        "data/security_work_checklist_templates.xml",
    ],
    "installable": True,
    "application": False,
}
