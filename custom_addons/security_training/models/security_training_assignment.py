from odoo import api, fields, models
from odoo.exceptions import UserError


class SecurityTrainingAssignment(models.Model):
    """Pins course_version_id at creation time -- this is the version
    pinning behaviour BUILD-STATUS-AND-PHASE-PLAN.md Phase 4.2 calls for.
    Publishing a new version of the course never changes what an assignee
    sees or is assessed against; a supervisor has to explicitly reassign to
    move someone onto the new version."""

    _name = "security.training.assignment"
    _description = "Training Assignment"
    _inherit = ["mail.thread"]
    _order = "due_date, id"

    employee_id = fields.Many2one("hr.employee", required=True, tracking=True)
    course_id = fields.Many2one(
        "security.training.course", required=True,
        help="Denormalised for reporting; the version below is authoritative for content.",
    )
    course_version_id = fields.Many2one(
        "security.training.course.version", required=True, readonly=True,
        help="Pinned at assignment time. Never changes after creation.",
    )
    due_date = fields.Date()
    state = fields.Selection(
        [
            ("assigned", "Assigned"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
        default="assigned",
        required=True,
        tracking=True,
    )
    lesson_progress_ids = fields.One2many("security.training.lesson.progress", "assignment_id")
    attempt_ids = fields.One2many("security.training.attempt", "assignment_id")
    completed_at = fields.Datetime(readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("course_version_id") and vals.get("course_id"):
                course = self.env["security.training.course"].browse(vals["course_id"])
                if not course.published_version_id:
                    raise UserError(
                        f"'{course.name}' has no published version yet -- nothing to assign."
                    )
                vals["course_version_id"] = course.published_version_id.id
        return super().create(vals_list)

    def action_mark_in_progress(self):
        self.filtered(lambda a: a.state == "assigned").write({"state": "in_progress"})

    def _check_completion(self):
        """An assignment completes once every lesson is progressed and every
        assessment has a passed attempt. Called after logging progress or an
        attempt result -- not a cron, since it only ever needs to run right
        after one of those two things changes."""
        for assignment in self:
            if assignment.state == "completed":
                continue
            version = assignment.course_version_id
            all_lessons = version.section_ids.mapped("lesson_ids")
            done_lesson_ids = set(assignment.lesson_progress_ids.mapped("lesson_id").ids)
            lessons_done = all(lesson.id in done_lesson_ids for lesson in all_lessons)

            all_assessments = version.assessment_ids
            assessments_passed = all(
                any(
                    attempt.assessment_id == assessment and attempt.state == "passed"
                    for attempt in assignment.attempt_ids
                )
                for assessment in all_assessments
            )

            if lessons_done and assessments_passed:
                assignment.write({"state": "completed", "completed_at": fields.Datetime.now()})
                assignment.env["security.training.competency"]._grant_from_assignment(assignment)


class SecurityTrainingLessonProgress(models.Model):
    _name = "security.training.lesson.progress"
    _description = "Training Lesson Progress"

    assignment_id = fields.Many2one("security.training.assignment", required=True, ondelete="cascade")
    lesson_id = fields.Many2one("security.training.lesson", required=True, ondelete="cascade")
    completed_at = fields.Datetime(default=fields.Datetime.now, required=True)

    _assignment_lesson_unique = models.Constraint(
        "unique(assignment_id, lesson_id)", "This lesson is already marked complete for this assignment."
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.assignment_id.write({"state": "in_progress"})
        records.assignment_id._check_completion()
        return records


class SecurityTrainingAttempt(models.Model):
    _name = "security.training.attempt"
    _description = "Training Assessment Attempt"
    _order = "assignment_id, attempt_number"

    assignment_id = fields.Many2one("security.training.assignment", required=True, ondelete="cascade")
    assessment_id = fields.Many2one("security.training.assessment", required=True, ondelete="cascade")
    attempt_number = fields.Integer(required=True)
    state = fields.Selection(
        [("in_progress", "In Progress"), ("passed", "Passed"), ("failed", "Failed")],
        default="in_progress", required=True,
    )
    score_pct = fields.Float(readonly=True)
    answer_ids = fields.One2many("security.training.attempt.answer", "attempt_id")
    submitted_at = fields.Datetime(readonly=True)

    @api.model
    def action_start_attempt(self, assignment_id, assessment_id):
        assignment = self.env["security.training.assignment"].browse(assignment_id)
        assessment = self.env["security.training.assessment"].browse(assessment_id)
        prior = self.search_count([
            ("assignment_id", "=", assignment_id), ("assessment_id", "=", assessment_id),
        ])
        if prior >= assessment.max_attempts:
            raise UserError(
                f"No attempts left for '{assessment.name}' ({assessment.max_attempts} allowed)."
            )
        return self.create({
            "assignment_id": assignment_id, "assessment_id": assessment_id,
            "attempt_number": prior + 1,
        })

    def action_submit(self, answers):
        """answers: {question_id: [selected_option_id, ...]}"""
        self.ensure_one()
        if self.state != "in_progress":
            raise UserError("This attempt has already been submitted.")

        questions = self.assessment_id.question_ids
        correct_count = 0
        for question in questions:
            selected = set(answers.get(question.id, answers.get(str(question.id), [])))
            correct = set(question.option_ids.filtered("is_correct").ids)
            if selected == correct:
                correct_count += 1
            self.env["security.training.attempt.answer"].create({
                "attempt_id": self.id, "question_id": question.id,
                "selected_option_ids": [(6, 0, list(selected))],
            })

        score_pct = (correct_count / len(questions) * 100.0) if questions else 0.0
        passed = score_pct >= self.assessment_id.pass_mark_pct
        self.write({
            "state": "passed" if passed else "failed",
            "score_pct": score_pct,
            "submitted_at": fields.Datetime.now(),
        })
        self.assignment_id._check_completion()

        if not passed and self.assignment_id.state != "completed":
            attempts_used = len(self.assignment_id.attempt_ids.filtered(
                lambda a: a.assessment_id == self.assessment_id
            ))
            if attempts_used >= self.assessment_id.max_attempts:
                self.assignment_id.write({"state": "failed"})
        return self


class SecurityTrainingAttemptAnswer(models.Model):
    _name = "security.training.attempt.answer"
    _description = "Training Attempt Answer"

    attempt_id = fields.Many2one("security.training.attempt", required=True, ondelete="cascade")
    question_id = fields.Many2one("security.training.question", required=True, ondelete="cascade")
    selected_option_ids = fields.Many2many("security.training.question.option")
