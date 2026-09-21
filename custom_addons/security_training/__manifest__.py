{
    "name": "DeployGuard Training",
    "summary": "Course authoring, assignment and assessment (BUILD-ORDER P3 slice)",
    "version": "19.0.1.0.0",
    "category": "Human Resources",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "description": """
        docs/deployguard/BUILD-STATUS-AND-PHASE-PLAN.md Phase 4 / BUILD-ORDER
        P3, scoped to what an ERP module can deliver on its own (no Platform
        worker or desktop lesson player yet):

        - security.training.course / .course.version / .section / .lesson:
          versioned course content. A course version is draft -> in_review ->
          published -> archived; only published versions can be assigned.
        - security.training.assessment / .question / .question.option:
          single/multiple-choice assessments per course version.
        - security.training.assignment: pins the course VERSION at
          assignment time, so publishing a new version never changes
          content someone is already partway through.
        - security.training.attempt / .attempt.answer: scored attempts,
          bounded by the assessment's max_attempts.
        - security.training.competency: evidence-linked to the EXISTING
          security.employee.certification model (security_base) rather than
          a duplicate.

        Deliberately NOT here: the desktop lesson player and assessment
        runner (needs the desktop app, a separate track), real DogForce
        course content (needs the ops manager, OQ-19 in the planning docs),
        and adaptive/AI-authored content (V1/V2 by design).
    """,
    "depends": ["security_base", "mail"],
    "data": [
        "security/security_groups.xml",
        "security/ir.model.access.csv",
        "views/security_training_course_views.xml",
        "views/security_training_assignment_views.xml",
        "views/security_training_competency_views.xml",
        "views/security_training_menu.xml",
        "data/security_training_dogforce_course.xml",
        "data/security_training_cron.xml",
    ],
    "installable": True,
    "application": False,
}
