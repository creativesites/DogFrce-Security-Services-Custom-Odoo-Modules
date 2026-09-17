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
        BUILD-STATUS-AND-PHASE-PLAN.md Phase 3 adds, in this Odoo-native
        slice (not the Platform worker the paragraph above originally
        assumed):
        - security.work.schedule.rule: calendar recurrence (fixed weekdays,
          fixed assignee) over a rolling 7-day horizon. Shift-based and
          site-event-based recurrence are NOT implemented -- see that
          model's docstring for why a heuristic wasn't attempted instead.
        - Auto-completion: security.work.task is a security.bus.subscriber
          for "attendance.batch.reviewed"/"attendance.batch.locked" (now
          emitted by security_attendance), auto-verifying matching
          attendance.post tasks. Incident-triggered auto-completion is not
          implemented -- security_discipline emits no incident lifecycle
          events yet.
        - Evidence: a size limit on checklist photo evidence, and a
          retention cron that purges photos (not answers) from closed
          tasks past a configurable age.
        - A verify queue action and an overdue sweep that flags a task
          once via chatter + activity.
        - Record rules on security.work.checklist.response, which
          previously had none -- any employee could read or edit any other
          employee's checklist answers by record id.
        Still not here: offline sync (needs the desktop's own SQLCipher/
        outbox work, BUILD-STATUS-AND-PHASE-PLAN.md Phase 3.7-3.9) and
        site-event-based recurrence.
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
        "views/security_work_schedule_rule_views.xml",
        "views/security_work_menu.xml",
        "data/security_work_checklist_templates.xml",
        "data/security_work_cron.xml",
    ],
    "installable": True,
    "application": False,
}
