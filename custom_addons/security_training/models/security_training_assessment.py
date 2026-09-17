from odoo import api, fields, models


class SecurityTrainingAssessment(models.Model):
    _name = "security.training.assessment"
    _description = "Training Assessment"
    _order = "course_version_id, id"

    course_version_id = fields.Many2one("security.training.course.version", required=True, ondelete="cascade")
    name = fields.Char(required=True)
    pass_mark_pct = fields.Float(default=80.0, required=True)
    max_attempts = fields.Integer(default=3, required=True)
    question_ids = fields.One2many("security.training.question", "assessment_id", string="Questions")
    question_count = fields.Integer(compute="_compute_question_count")

    @api.depends("question_ids")
    def _compute_question_count(self):
        for a in self:
            a.question_count = len(a.question_ids)


class SecurityTrainingQuestion(models.Model):
    _name = "security.training.question"
    _description = "Training Question"
    _order = "assessment_id, sequence, id"

    assessment_id = fields.Many2one("security.training.assessment", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    text = fields.Text(required=True)
    question_type = fields.Selection(
        [("single", "Single choice"), ("multi", "Multiple choice")], default="single", required=True
    )
    option_ids = fields.One2many("security.training.question.option", "question_id", string="Options")


class SecurityTrainingQuestionOption(models.Model):
    _name = "security.training.question.option"
    _description = "Training Question Option"
    _order = "question_id, sequence, id"

    question_id = fields.Many2one("security.training.question", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    text = fields.Char(required=True)
    is_correct = fields.Boolean(default=False)
