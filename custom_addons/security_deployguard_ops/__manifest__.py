{
    "name": "DeployGuard Operations (V2)",
    "summary": "The roster, turned into guided, measurable, teachable work: DogForce's attendance pipeline",
    "description": """
        The first DeployGuard V2 vertical slice
        (docs/deployguard/dogforce-roles-and-pipeline.md):

            Roster -> Register attendance (Operations Supervisor)
                   -> Confirm attendance (Admin)
                   -> Verify attendance (HR)
                   -> the GM sees where each site is stuck

        Composes the generic pieces:
        - security_work: responsibilities create one task per rostered site-day.
        - security_attendance: the posting sheet's real state completes those
          tasks. DeployGuard checks the records; nobody ticks a box to claim
          it was done.
        - security_guidance: a guided flow for each step, verified against the
          same records.
        - security_training: "learn this first" when a duty needs a course,
          and the Daily Attendance course with guided practice.
        - security_exceptions: overdue work becomes an exception with owner,
          evidence and next action.
        A setup wizard lets the GM assign the three steps to people in one go.
    """,
    "version": "19.0.1.0.0",
    "category": "Security/Operations",
    "author": "DogForce Security Services",
    "license": "LGPL-3",
    "depends": [
        "security_work",
        "security_attendance",
        "security_training",
        "security_guidance",
        "security_notifications",
        "security_exceptions",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/checklist_templates.xml",
        "data/guidance_flows.xml",
        "data/exception_rules.xml",
        "data/cron.xml",
        "data/training_course.xml",
        "views/responsibility_views.xml",
        "wizard/pipeline_setup_views.xml",
    ],
    "installable": True,
    "application": False,
}
