from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SecurityClientContract(models.Model):
    _name = "security.client.contract"
    _description = "Security Client Contract"
    _order = "date_start desc"

    name = fields.Char(required=True, string="Contract Reference")
    partner_id = fields.Many2one("res.partner", required=True, string="Client")
    site_id = fields.Many2one(
        "security.client.site",
        string="Site",
        domain="[('partner_id', '=', partner_id)]",
        help="Leave blank for a client-wide contract covering all sites.",
    )
    date_start = fields.Date(required=True, string="Start Date")
    date_end = fields.Date(string="End Date")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("expired", "Expired"),
            ("terminated", "Terminated"),
        ],
        default="draft",
        required=True,
    )
    monthly_value = fields.Float(string="Monthly Value")
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
    )
    billing_this_period = fields.Float(
        compute="_compute_billing_cap",
        string="Billed This Month",
        digits=(10, 2),
    )
    cap_used_pct = fields.Float(
        compute="_compute_billing_cap",
        string="Cap Used (%)",
        digits=(5, 1),
    )
    cap_exceeded = fields.Boolean(
        compute="_compute_billing_cap",
        string="Cap Exceeded",
    )
    note = fields.Text()

    def _compute_billing_cap(self):
        from datetime import date
        today = date.today()
        first_day = today.replace(day=1)
        attendance_model = self.env.get("security.attendance.record")
        for contract in self:
            billed = 0.0
            if attendance_model and contract.site_id:
                records = attendance_model.search([
                    ("site_id", "=", contract.site_id.id),
                    ("shift_date", ">=", str(first_day)),
                    ("shift_date", "<=", str(today)),
                    ("status", "in", ["present", "late", "early_leave"]),
                ])
                for rec in records:
                    hours = 0.0
                    if hasattr(rec, "shift_template_id") and rec.shift_template_id:
                        tmpl = rec.shift_template_id
                        end = tmpl.end_hour if hasattr(tmpl, "end_hour") else 8.0
                        start = tmpl.start_hour if hasattr(tmpl, "start_hour") else 0.0
                        hours = max(0.0, end - start)
                    else:
                        hours = 8.0
                    if hasattr(rec, "bill_rate") and rec.bill_rate:
                        billed += hours * rec.bill_rate
                    elif hasattr(rec, "roster_slot_id") and rec.roster_slot_id and hasattr(rec.roster_slot_id, "shift_requirement_id"):
                        req = rec.roster_slot_id.shift_requirement_id
                        if req and hasattr(req, "bill_rate"):
                            billed += hours * req.bill_rate
            contract.billing_this_period = billed
            cap = contract.monthly_value
            if cap and cap > 0:
                contract.cap_used_pct = round(billed / cap * 100, 1)
                contract.cap_exceeded = billed > cap
            else:
                contract.cap_used_pct = 0.0
                contract.cap_exceeded = False

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for contract in self:
            if contract.date_end and contract.date_end < contract.date_start:
                raise ValidationError("Contract end date cannot be before start date.")

    def _is_active_for_date(self, target_date):
        """Return True if this contract is active on target_date."""
        self.ensure_one()
        if self.state != "active":
            return False
        if target_date < self.date_start:
            return False
        if self.date_end and target_date > self.date_end:
            return False
        return True

    def get_active_for_site(self, site, target_date):
        """
        Return active contract for site on target_date, or empty recordset.

        Preference: site-specific contract > client-wide contract.
        """
        contracts = self.search([
            ("partner_id", "=", site.partner_id.id),
            ("state", "=", "active"),
            ("date_start", "<=", target_date),
            "|",
            ("date_end", "=", False),
            ("date_end", ">=", target_date),
        ])
        site_specific = contracts.filtered(lambda c: c.site_id == site)
        if site_specific:
            return site_specific[0]
        client_wide = contracts.filtered(lambda c: not c.site_id)
        if client_wide:
            return client_wide[0]
        return self.browse()

    def action_activate(self):
        for contract in self:
            contract.state = "active"

    def action_terminate(self):
        for contract in self:
            contract.state = "terminated"

    def action_reset_to_draft(self):
        for contract in self:
            contract.state = "draft"
