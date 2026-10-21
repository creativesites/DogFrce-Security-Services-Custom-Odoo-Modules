from datetime import timedelta
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class SecurityContractAdhocRequest(models.Model):
    _name = "security.contract.adhoc.request"
    _description = "Ad-Hoc / Additional Guard Request"
    _order = "date_start desc, id desc"

    name = fields.Char(
        string="Request Reference",
        required=True,
        copy=False,
        readonly=True,
        default="New",
    )
    contract_id = fields.Many2one(
        "security.client.contract",
        string="Client Contract",
        required=True,
        ondelete="cascade",
        index=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Client",
        related="contract_id.partner_id",
        store=True,
    )
    site_id = fields.Many2one(
        "security.client.site",
        string="Deployment Site",
        required=True,
    )
    post_id = fields.Many2one(
        "security.post",
        string="Post Position",
        domain="[('site_id', '=', site_id)]",
        help="Optional specific post position. If left empty, the site's default post is used.",
    )
    shift_template_id = fields.Many2one(
        "security.shift.template",
        string="Shift Template",
        required=True,
    )
    date_start = fields.Date(
        string="Start Date",
        required=True,
        default=fields.Date.today,
    )
    date_end = fields.Date(
        string="End Date",
        required=True,
        default=fields.Date.today,
    )
    guard_count = fields.Integer(
        string="Additional Guards",
        default=1,
        required=True,
    )
    bill_rate = fields.Float(
        string="Hourly Bill Rate (NAD)",
        help="Ad-hoc hourly bill rate. If zero, standard contract rate applies.",
    )
    reason = fields.Text(
        string="Request Reason / Client Ref",
        required=True,
    )
    note = fields.Text("Internal Operational Notes")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("scheduled", "Roster Generated"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
    )
    slot_ids = fields.One2many(
        "security.roster.slot",
        "adhoc_request_id",
        string="Generated Slots",
    )
    slots_count = fields.Integer(
        compute="_compute_slot_counts",
        string="Total Slots",
    )
    slots_assigned_count = fields.Integer(
        compute="_compute_slot_counts",
        string="Assigned Slots",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == "New":
                seq = self.env["ir.sequence"].next_by_code("security.contract.adhoc.request")
                if not seq:
                    count = self.search_count([]) + 1
                    seq = f"ADHOC-{count:04d}"
                vals["name"] = seq
        return super().create(vals_list)

    @api.constrains("date_start", "date_end", "guard_count")
    def _check_dates_and_counts(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_end < rec.date_start:
                raise ValidationError("End Date must be on or after Start Date.")
            if rec.guard_count <= 0:
                raise ValidationError("Additional guard count must be at least 1.")

    @api.onchange("contract_id")
    def _onchange_contract_id(self):
        if self.contract_id:
            # Pre-select first site under contract if available
            sites = self.contract_id.contract_site_ids.mapped("site_id")
            if not sites and self.contract_id.site_id:
                sites = self.contract_id.site_id
            if sites and not self.site_id:
                self.site_id = sites[0].id

    @api.onchange("site_id")
    def _onchange_site_id(self):
        if self.site_id:
            posts = self.site_id.post_ids.filtered("active")
            if posts and (not self.post_id or self.post_id not in posts):
                self.post_id = posts[0].id

    @api.depends("slot_ids", "slot_ids.employee_id")
    def _compute_slot_counts(self):
        for rec in self:
            rec.slots_count = len(rec.slot_ids)
            rec.slots_assigned_count = len(rec.slot_ids.filtered("employee_id"))

    def action_confirm(self):
        for rec in self:
            if not rec.date_start or not rec.date_end:
                raise UserError("Start Date and End Date are required.")
            if rec.guard_count <= 0:
                raise UserError("Guard count must be at least 1.")
            rec.state = "confirmed"

    def action_generate_slots(self):
        """Generate operational roster slots for this ad-hoc request."""
        self.ensure_one()
        if self.date_end < self.date_start:
            raise UserError("End date cannot be earlier than start date.")

        slot_model = self.env["security.roster.slot"]
        post = self.post_id
        if not post:
            post = self.site_id.post_ids.filtered("active")[:1]
        if not post:
            post_type = self.env["security.post.type"].search([], limit=1)
            post = self.env["security.post"].create({
                "name": f"Ad-Hoc Post — {self.name}",
                "site_id": self.site_id.id,
                "partner_id": self.partner_id.id,
                "post_type_id": post_type.id if post_type else False,
            })
            self.post_id = post.id

        current_date = self.date_start
        created_slots = slot_model
        while current_date <= self.date_end:
            # Look up active batch for this site/date
            batch = self.env["security.roster.batch"].search([
                ("site_id", "=", self.site_id.id),
                ("date_from", "<=", current_date),
                ("date_to", ">=", current_date),
                ("state", "!=", "cancelled"),
            ], limit=1)
            if not batch:
                batch = self.env["security.roster.batch"].search([
                    ("date_from", "<=", current_date),
                    ("date_to", ">=", current_date),
                    ("state", "!=", "cancelled"),
                ], limit=1)

            for _ in range(self.guard_count):
                vals = {
                    "site_id": self.site_id.id,
                    "partner_id": self.partner_id.id,
                    "post_id": post.id,
                    "shift_template_id": self.shift_template_id.id,
                    "shift_date": current_date,
                    "is_relief": True,
                    "override_reason": f"Ad-hoc request {self.name}: {self.reason or ''}",
                    "fairness_warning": "Ad-Hoc Additional Guard",
                    "adhoc_request_id": self.id,
                    "state": "draft",
                }
                if batch:
                    vals["batch_id"] = batch.id
                slot = slot_model.create(vals)
                created_slots |= slot
            current_date += timedelta(days=1)

        self.state = "scheduled"
        return {
            "type": "ir.actions.act_window",
            "name": f"Roster Slots for {self.name}",
            "res_model": "security.roster.slot",
            "view_mode": "list,form",
            "domain": [("adhoc_request_id", "=", self.id)],
            "target": "current",
        }

    def action_view_slots(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Roster Slots for {self.name}",
            "res_model": "security.roster.slot",
            "view_mode": "list,form",
            "domain": [("adhoc_request_id", "=", self.id)],
            "target": "current",
        }

    def action_cancel(self):
        for rec in self:
            # Unlink uncompleted slots
            uncompleted = rec.slot_ids.filtered(lambda s: s.state != "completed")
            uncompleted.unlink()
            rec.state = "cancelled"

    def action_reset_draft(self):
        for rec in self:
            rec.state = "draft"
