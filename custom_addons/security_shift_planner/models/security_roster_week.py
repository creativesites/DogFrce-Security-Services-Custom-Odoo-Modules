from datetime import timedelta

from odoo import api, fields, models


class SecurityRosterWeek(models.Model):
    _name = "security.roster.week"
    _description = "Weekly Roster Review Snapshot"
    _order = "week_start desc, id desc"
    _rec_name = "display_name"

    batch_id = fields.Many2one(
        "security.roster.batch",
        string="Roster Batch",
        ondelete="set null",
    )
    week_start = fields.Date(required=True, string="Week Start (Monday)")
    week_end = fields.Date(compute="_compute_week_end", store=True, string="Week End (Sunday)")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("reviewed", "Reviewed"),
            ("confirmed", "Confirmed"),
        ],
        default="draft",
        required=True,
    )
    reviewer_id = fields.Many2one("res.users", string="Reviewer", readonly=True)
    review_notes = fields.Text(string="Review Notes")
    reviewed_at = fields.Datetime(string="Reviewed At", readonly=True)
    gap_count_snap = fields.Integer(string="Critical Gaps (snapshot)", default=0)
    display_name = fields.Char(compute="_compute_display_name", string="Week")

    @api.depends("week_start")
    def _compute_week_end(self):
        for rec in self:
            rec.week_end = rec.week_start + timedelta(days=6) if rec.week_start else False

    @api.depends("week_start", "batch_id")
    def _compute_display_name(self):
        for rec in self:
            if rec.week_start:
                label = f"Week of {rec.week_start.strftime('%d %b %Y')}"
                if rec.batch_id:
                    label += f" — {rec.batch_id.name}"
                rec.display_name = label
            else:
                rec.display_name = "New Week Review"

    def action_review(self):
        for rec in self:
            rec.reviewer_id = self.env.user
            rec.reviewed_at = fields.Datetime.now()
            rec.state = "reviewed"

    def action_confirm_week(self):
        for rec in self:
            if rec.state == "draft":
                rec.reviewer_id = self.env.user
                rec.reviewed_at = fields.Datetime.now()
            rec.state = "confirmed"
            if rec.batch_id and hasattr(rec.batch_id, "critical_gap_count"):
                rec.gap_count_snap = rec.batch_id.critical_gap_count

    def action_reset_to_draft(self):
        for rec in self:
            rec.state = "draft"
