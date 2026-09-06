from odoo import _, api, fields, models


class SecurityTelephonyCall(models.Model):
    _name = "security.telephony.call"
    _description = "Telephony Call Log"
    _inherit = ["mail.thread"]
    _order = "started_at desc, id desc"
    _check_company_auto = True

    name = fields.Char(required=True, copy=False, default="New")
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)

    # pbx_call_id is the PBX's own channel/call identifier. Webhook events
    # for the same call arrive multiple times (ringing -> answered ->
    # hangup) and must update one record, not create three — this is the
    # idempotency key. Whatever PBX gets connected, its call ID goes here.
    pbx_call_id = fields.Char(index=True, copy=False)

    direction = fields.Selection(
        [("inbound", "Inbound"), ("outbound", "Outbound")],
        default="inbound", required=True,
    )
    from_number = fields.Char()
    to_number = fields.Char()

    caller_name = fields.Char(help="Resolved automatically from from_number when it matches an employee or client.")
    employee_id = fields.Many2one("hr.employee", check_company=True)
    partner_id = fields.Many2one("res.partner", check_company=True)

    state = fields.Selection(
        [
            ("ringing", "Ringing"),
            ("answered", "Answered"),
            ("missed", "Missed"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
        default="ringing", required=True, tracking=True,
    )
    started_at = fields.Datetime(default=fields.Datetime.now, required=True)
    answered_at = fields.Datetime(readonly=True)
    ended_at = fields.Datetime(readonly=True)
    duration_seconds = fields.Integer(compute="_compute_duration", store=True)

    recording_url = fields.Char()
    dispatch_id = fields.Many2one("security.response.dispatch", string="Linked Dispatch", check_company=True, tracking=True)
    notes = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("security.telephony.call") or "New"
        return super().create(vals_list)

    @api.depends("answered_at", "ended_at")
    def _compute_duration(self):
        for call in self:
            if call.answered_at and call.ended_at:
                call.duration_seconds = int((call.ended_at - call.answered_at).total_seconds())
            else:
                call.duration_seconds = 0

    def _resolve_caller_identity(self):
        """Reuses the WhatsApp bridge's own phone-matching logic rather
        than a second copy of it — one place that decides how a raw phone
        number maps to an employee/client across the whole platform."""
        self.ensure_one()
        bridge = self.env["security.whatsapp.bridge"].sudo()
        name, employee_id, partner_id = bridge._resolve_sender_identity(self.from_number)
        self.write({
            "caller_name": name or self.from_number,
            "employee_id": employee_id or False,
            "partner_id": partner_id or False,
        })

    def action_create_dispatch(self):
        """Deliberately a manual action, not something the inbound webhook
        does automatically — not every call is a callout, and deciding
        that is the controller's call, not the phone system's.

        Opens a blank, unsaved dispatch form pre-filled with the caller's
        details rather than creating the record server-side — site_id is
        required on a dispatch (you can't dispatch a unit nowhere), and
        that's exactly the piece a controller still needs to ask the
        caller for. Link this call to the dispatch (the dispatch_id field
        below) once it's saved.
        """
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "security.response.dispatch",
            "views": [[False, "form"]],
            "target": "current",
            "context": {
                "default_source": "phone_call",
                "default_caller_name": self.caller_name,
                "default_caller_number": self.from_number,
                "default_notes": _("Raised from call %s.") % self.name,
            },
        }
