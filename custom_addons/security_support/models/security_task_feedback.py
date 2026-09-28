from odoo import api, fields, models
from odoo.exceptions import UserError

RATINGS = [
    ("easy", "Easy"),
    ("okay", "Okay"),
    ("difficult", "Difficult"),
    ("could_not_complete", "Couldn't complete"),
]
DIFFICULTY_REASONS = [
    ("unclear_instructions", "Unclear instructions"),
    ("system_slow_or_buggy", "System slow or showed an error"),
    ("site_conditions", "Site access or conditions"),
    ("time_pressure", "Not enough time"),
    ("missing_equipment", "Something needed was missing"),
    ("other", "Other"),
]


class SecurityTaskFeedback(models.Model):
    """The optional one-tap "how was that?" after submitting a task.

    It shows which tasks are hard and why, so training and instructions can be
    improved. It is not a per-person performance measure, and nothing in
    adoption scoring reads it."""

    _name = "security.task.feedback"
    _description = "Task Feedback"
    _order = "create_date desc"

    task_id = fields.Many2one("security.work.task", required=True, ondelete="cascade", index=True)
    responsibility_name = fields.Char(related="task_id.responsibility_id.name", store=True, string="Duty")
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user, readonly=True)
    rating = fields.Selection(RATINGS, required=True)
    difficulty_reason = fields.Selection(DIFFICULTY_REASONS)
    notes = fields.Char()

    @api.model
    def submit_feedback(self, payload):
        if not isinstance(payload, dict) or payload.get("rating") not in dict(RATINGS):
            raise UserError(self.env._("Choose how the task went."))
        task = self.env["security.work.task"].search([("id", "=", int(payload.get("task_id") or 0))], limit=1)
        if not task:
            raise UserError(self.env._("That task isn't one of yours."))
        reason = payload.get("difficulty_reason")
        rec = self.create({
            "task_id": task.id,
            "rating": payload["rating"],
            "difficulty_reason": reason if reason in dict(DIFFICULTY_REASONS) else False,
            "notes": (payload.get("notes") or "")[:500] or False,
        })
        return {"id": rec.id, "rating": rec.rating}
