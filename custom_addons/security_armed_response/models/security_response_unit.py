import uuid
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SecurityResponseUnit(models.Model):
    _name = "security.response.unit"
    _description = "Armed Response Unit"
    _order = "name"
    _check_company_auto = True

    name = fields.Char(required=True, help="Unit callsign, e.g. 'Alpha 1'.")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    commander_id = fields.Many2one(
        "hr.employee", required=True, string="Unit Commander",
        domain=[("security_guard", "=", True)], check_company=True,
    )
    member_ids = fields.Many2many(
        "hr.employee", "security_response_unit_member_rel", "unit_id", "employee_id",
        string="Unit Members", domain=[("security_guard", "=", True)],
    )
    vehicle_id = fields.Many2one("security.vehicle", string="Assigned Vehicle")
    base_site_id = fields.Many2one(
        "security.client.site", string="Home Base / Standby Site", check_company=True,
        help="Where this unit is stationed when not dispatched.",
    )
    status = fields.Selection(
        [
            ("available", "Available"),
            ("dispatched", "Dispatched"),
            ("on_scene", "On Scene"),
            ("returning", "Returning"),
            ("off_duty", "Off Duty"),
        ],
        default="available", required=True, tracking=True,
    )
    active_dispatch_id = fields.Many2one(
        "security.response.dispatch", string="Current Dispatch",
        compute="_compute_active_dispatch", store=True,
    )
    dispatch_ids = fields.One2many("security.response.dispatch", "unit_id", string="Dispatch History")
    dispatch_count = fields.Integer(compute="_compute_dispatch_count")

    # ── Live position ─────────────────────────────────────────────────
    # Populated manually for now (or via the /api/armed_response endpoint
    # below with gps_token) until a GPS provider is chosen — see
    # controllers/gps_ping.py. The map only cares about these three
    # fields, so swapping in a real feed later is a data-source change,
    # not a UI change.
    last_lat = fields.Float("Last Latitude", digits=(10, 6))
    last_lng = fields.Float("Last Longitude", digits=(10, 6))
    last_position_at = fields.Datetime("Last Position Update", readonly=True)
    gps_token = fields.Char(
        readonly=True, copy=False, default=lambda self: str(uuid.uuid4()),
        help="Shared secret this unit's tracker/device uses to authenticate position pings. "
             "Rotate via 'Regenerate GPS Token' if it leaks.",
    )
    position_is_stale = fields.Boolean(compute="_compute_position_is_stale")

    @api.depends("last_position_at")
    def _compute_position_is_stale(self):
        stale_after = timedelta(minutes=15)
        now = fields.Datetime.now()
        for unit in self:
            unit.position_is_stale = bool(
                not unit.last_position_at or (now - unit.last_position_at) > stale_after
            )

    def action_regenerate_gps_token(self):
        for unit in self:
            unit.gps_token = str(uuid.uuid4())

    @api.depends("dispatch_ids.state")
    def _compute_active_dispatch(self):
        for unit in self:
            open_dispatch = unit.dispatch_ids.filtered(
                lambda d: d.state not in ("resolved", "cancelled")
            )
            unit.active_dispatch_id = open_dispatch[:1]

    def _compute_dispatch_count(self):
        for unit in self:
            unit.dispatch_count = len(unit.dispatch_ids)

    @api.constrains("status", "active_dispatch_id")
    def _check_status_consistency(self):
        for unit in self:
            if unit.status == "available" and unit.active_dispatch_id:
                raise ValidationError(
                    "%s cannot be marked Available while it has an open dispatch (%s)."
                    % (unit.name, unit.active_dispatch_id.name)
                )

    def action_view_dispatches(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Dispatch History — %s" % self.name,
            "res_model": "security.response.dispatch",
            "view_mode": "list,form",
            "domain": [("unit_id", "=", self.id)],
        }
