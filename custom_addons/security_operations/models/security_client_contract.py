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
    note = fields.Text()

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
