from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SecurityResponseDispatch(models.Model):
    _name = "security.response.dispatch"
    _description = "Armed Response Dispatch"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"
    _check_company_auto = True

    name = fields.Char(required=True, copy=False, default="New")
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)

    source = fields.Selection(
        [
            ("panic_button", "Panic Button"),
            ("phone_call", "Phone Call"),
            ("incident", "Linked Incident"),
            ("manual", "Manual / Walk-in"),
        ],
        default="phone_call", required=True, tracking=True,
    )
    site_id = fields.Many2one("security.client.site", required=True, check_company=True, tracking=True)
    incident_id = fields.Many2one("security.incident", string="Linked Incident")
    unit_id = fields.Many2one("security.response.unit", string="Assigned Unit", check_company=True, tracking=True)

    caller_name = fields.Char()
    caller_number = fields.Char(
        help="Captured manually until telephony integration is wired up.",
    )

    priority = fields.Selection(
        [("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")],
        default="medium", required=True, tracking=True,
    )
    state = fields.Selection(
        [
            ("new", "New"),
            ("acknowledged", "Acknowledged"),
            ("dispatched", "Dispatched"),
            ("on_scene", "On Scene"),
            ("resolved", "Resolved"),
            ("cancelled", "Cancelled"),
        ],
        default="new", required=True, tracking=True,
    )

    acknowledged_at = fields.Datetime(readonly=True)
    dispatched_at = fields.Datetime(readonly=True)
    on_scene_at = fields.Datetime(readonly=True)
    resolved_at = fields.Datetime(readonly=True)

    response_time_minutes = fields.Integer(
        string="Response Time (min)", compute="_compute_response_time", store=True,
        help="Minutes between dispatch and arrival on scene.",
    )
    notes = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("security.response.dispatch") or "New"
        return super().create(vals_list)

    @api.depends("dispatched_at", "on_scene_at")
    def _compute_response_time(self):
        for dispatch in self:
            if dispatch.dispatched_at and dispatch.on_scene_at:
                delta = dispatch.on_scene_at - dispatch.dispatched_at
                dispatch.response_time_minutes = round(delta.total_seconds() / 60)
            else:
                dispatch.response_time_minutes = 0

    def action_acknowledge(self):
        for dispatch in self:
            if dispatch.state != "new":
                continue
            dispatch.write({"state": "acknowledged", "acknowledged_at": fields.Datetime.now()})
            dispatch.message_post(body=_("Callout acknowledged by %s.") % self.env.user.name)

    def action_dispatch(self):
        for dispatch in self:
            if not dispatch.unit_id:
                raise UserError(_("Assign a response unit before dispatching."))
            if dispatch.unit_id.status not in ("available",):
                raise UserError(
                    _("%s is not available (currently: %s).")
                    % (dispatch.unit_id.name, dispatch.unit_id.status)
                )
            dispatch.write({"state": "dispatched", "dispatched_at": fields.Datetime.now()})
            dispatch.unit_id.status = "dispatched"
            dispatch.message_post(
                body=_("Dispatched %s to %s.") % (dispatch.unit_id.name, dispatch.site_id.name)
            )

    def action_mark_on_scene(self):
        for dispatch in self:
            if dispatch.state != "dispatched":
                continue
            dispatch.write({"state": "on_scene", "on_scene_at": fields.Datetime.now()})
            if dispatch.unit_id:
                dispatch.unit_id.status = "on_scene"
            dispatch.message_post(body=_("Unit is on scene."))

    def action_resolve(self):
        for dispatch in self:
            dispatch.write({"state": "resolved", "resolved_at": fields.Datetime.now()})
            if dispatch.unit_id:
                dispatch.unit_id.status = "available"
            dispatch.message_post(body=_("Callout resolved by %s.") % self.env.user.name)

    def action_cancel(self):
        for dispatch in self:
            dispatch.write({"state": "cancelled"})
            if dispatch.unit_id and dispatch.unit_id.status in ("dispatched", "on_scene"):
                dispatch.unit_id.status = "available"
            dispatch.message_post(body=_("Callout cancelled by %s.") % self.env.user.name)
