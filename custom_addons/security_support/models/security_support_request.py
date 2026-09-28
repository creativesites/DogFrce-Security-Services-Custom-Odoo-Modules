import json

from odoo import api, fields, models
from odoo.exceptions import UserError

CLIENT_CATEGORIES = [
    ("not_working", "Not working"),
    ("dont_understand", "Don't understand"),
    ("no_permission", "No permission"),
    ("cant_find", "Can't find"),
    ("my_info_wrong", "My info is wrong"),
    ("slow", "System is slow"),
    ("other", "Other"),
]

# Diagnostics are sanitised by the desktop (src/lib/errorCollector.ts), but
# this is a server boundary, so it doesn't trust that. Keys that could carry
# credentials are dropped, and the blob is capped.
_FORBIDDEN_KEYS = {"password", "session_id", "cookie", "token", "secret", "authorization"}
_MAX_DIAGNOSTICS = 20000


def _scrub(value):
    if isinstance(value, dict):
        return {k: _scrub(v) for k, v in value.items() if str(k).lower() not in _FORBIDDEN_KEYS}
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    return value


class SecuritySupportRequest(models.Model):
    """An employee's "something's wrong" report
    (docs/deployguard/34-feedback-and-support.md)."""

    _name = "security.support.request"
    _description = "Support Request"
    _inherit = ["mail.thread"]
    _order = "create_date desc, id desc"

    name = fields.Char(readonly=True, copy=False, default="New")
    subject = fields.Char(required=True, tracking=True)
    description = fields.Text()
    client_category = fields.Selection(CLIENT_CATEGORIES, required=True, default="other", tracking=True)
    priority = fields.Selection(
        [("0", "Low"), ("1", "Normal"), ("2", "High"), ("3", "Urgent: blocked from working")],
        default="1", required=True, tracking=True,
    )
    state = fields.Selection(
        [("new", "New"), ("in_progress", "In progress"), ("resolved", "Resolved")],
        default="new", required=True, tracking=True,
    )
    user_id = fields.Many2one("res.users", string="Reported by", default=lambda self: self.env.user, readonly=True)
    employee_id = fields.Many2one("hr.employee", compute="_compute_employee_id", store=True)
    route = fields.Char(help="Which DeployGuard screen the report was made from.")
    work_task_id = fields.Many2one("security.work.task", string="About task", ondelete="set null")
    diagnostics = fields.Text(readonly=True, help="Sanitised technical details attached by the desktop, if the employee chose to.")
    system_fault = fields.Boolean(
        tracking=True,
        help="Set by support when the problem was the system's fault, not the employee's. "
             "Work they could not do because of it should be excused, not counted against them.",
    )
    resolution_note = fields.Text()
    resolved_at = fields.Datetime(readonly=True)

    @api.depends("user_id")
    def _compute_employee_id(self):
        for rec in self:
            rec.employee_id = rec.user_id.employee_ids[:1]

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env["ir.sequence"].sudo()
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = seq.next_by_code("security.support.request") or "New"
        return super().create(vals_list)

    @api.model
    def create_from_client(self, payload):
        """Desktop entry point. Only whitelisted fields are accepted; the
        reporter is always the calling user."""
        if not isinstance(payload, dict) or not (payload.get("subject") or "").strip():
            raise UserError(self.env._("Please give the problem a short summary."))
        category = payload.get("client_category")
        if category not in dict(CLIENT_CATEGORIES):
            category = "other"
        priority = payload.get("priority") if payload.get("priority") in ("0", "1", "2", "3") else "1"

        vals = {
            "subject": payload["subject"].strip()[:200],
            "description": (payload.get("description") or "").strip()[:5000] or False,
            "client_category": category,
            "priority": priority,
            "route": (payload.get("route") or "")[:100] or False,
        }
        task_id = payload.get("work_task_id")
        if task_id:
            # Only link a task the reporter can actually see.
            task = self.env["security.work.task"].search([("id", "=", int(task_id))], limit=1)
            vals["work_task_id"] = task.id or False
        if payload.get("diagnostics") is not None:
            vals["diagnostics"] = json.dumps(_scrub(payload["diagnostics"]), indent=2)[:_MAX_DIAGNOSTICS]

        rec = self.create(vals)
        return {"id": rec.id, "name": rec.name, "state": rec.state, "priority": rec.priority}

    def action_start(self):
        self.write({"state": "in_progress"})

    def action_resolve(self):
        self.write({"state": "resolved", "resolved_at": fields.Datetime.now()})

    def action_reopen(self):
        self.write({"state": "in_progress", "resolved_at": False})
