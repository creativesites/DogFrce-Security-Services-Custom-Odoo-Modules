from odoo import fields, models


class SecurityAIChatSession(models.Model):
    """One conversation thread per user. History persists across browser sessions."""
    _name = "security.ai.chat.session"
    _description = "AI Chat Session"
    _order = "last_activity desc"
    _rec_name = "display_name"

    user_id = fields.Many2one("res.users", required=True, default=lambda s: s.env.uid, index=True)
    started_at = fields.Datetime(default=fields.Datetime.now, required=True)
    last_activity = fields.Datetime(default=fields.Datetime.now)
    context_model = fields.Char(string="Started on Model")
    context_id = fields.Integer(string="Started on Record ID")
    message_ids = fields.One2many("security.ai.chat.message", "session_id")
    message_count = fields.Integer(compute="_compute_message_count", string="Messages")

    display_name = fields.Char(compute="_compute_display_name")

    def _compute_message_count(self):
        for s in self:
            s.message_count = len(s.message_ids.filtered(
                lambda m: m.role in ("user", "assistant")
            ))

    def _compute_display_name(self):
        for s in self:
            dt = s.started_at.strftime("%d %b %Y %H:%M") if s.started_at else "—"
            s.display_name = f"{s.user_id.name} — {dt}"


class SecurityAIChatMessage(models.Model):
    """One message (or tool interaction) within a chat session."""
    _name = "security.ai.chat.message"
    _description = "AI Chat Message"
    _order = "id asc"

    session_id = fields.Many2one(
        "security.ai.chat.session", required=True, ondelete="cascade", index=True
    )
    role = fields.Selection(
        [
            ("user", "User"),
            ("assistant", "Assistant"),
            ("pending_action", "Pending Action"),
        ],
        required=True,
        default="user",
    )
    content = fields.Text()
    components_json = fields.Text(string="Rendered Components (JSON)")
    tool_calls_json = fields.Text(string="Tool Calls (JSON)")
    timestamp = fields.Datetime(default=fields.Datetime.now, required=True)
