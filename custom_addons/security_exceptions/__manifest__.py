{
    "name": "DogForce Exceptions & Inbox",
    "summary": "Rule-driven exception engine with escalation, built on top of security_notifications' existing alerts -- not a second detection layer",
    "description": """
        docs/deployguard/BUILD-STATUS-AND-PHASE-PLAN.md Phase 6.

        Per 6.2 ("ingest rather than re-derive"), this module does NOT
        re-detect roster gaps, missed check-ins, expiries, AWOL, or
        override audits -- security_notifications already scans for all
        of those deterministically. Instead:

        - security.exception.rule maps each security.notification
          notification_type to a triage tier (critical/attention/watch)
          and an escalation policy.
        - security.exception.instance is created 1:1 from an open
          security.notification row (unique per notification_id -- the
          dedupe key), tracks acknowledge/resolve state, and auto-resolves
          the moment its source notification is dismissed or superseded.
        - security.exception.escalation.policy runs two escalation levels
          against a working calendar (a site or company's
          resource.calendar, via resource.calendar.get_work_hours_count --
          a real Odoo API, not a hand-rolled business-hours clock) when
          `use_working_calendar` is set; otherwise plain wall-clock
          minutes. Acknowledging an instance cancels further escalation.
        - Pause-on-stale-data: if the sync cron hasn't reconfirmed an
          instance's source notification within `stale_after_minutes`,
          escalation pauses (`stale_paused`) rather than escalating on
          data nobody has actually re-checked.

        Not built in this slice (see BUILD-STATUS-AND-PHASE-PLAN.md Phase
        6 status for the full breakdown):
        - Desktop manager/supervisor inbox UI (6.4) -- Odoo backend list
          views only, grouped by tier, same deferral pattern as
          security_adoption's Phase 5.7.
        - Desktop OS notifications via tauri-plugin-notification, and
          email deliverability (SPF/DKIM/DMARC) setup -- both need a
          desktop build environment / an email provider decision this
          session doesn't have (6.5, 6.6 are infra decisions, not code
          this module can make up an answer for).
    """,
    "version": "19.0.1.0.0",
    "category": "Security/Operations",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "depends": ["mail", "resource", "security_base", "security_notifications"],
    "data": [
        "security/security_groups.xml",
        "security/ir.model.access.csv",
        "security/security_exceptions_rules.xml",
        "data/security_exceptions_policies.xml",
        "data/security_exceptions_rules.xml",
        "data/security_exceptions_cron.xml",
        "views/security_exceptions_views.xml",
        "views/security_exceptions_menu.xml",
    ],
    "installable": True,
    "application": False,
}
