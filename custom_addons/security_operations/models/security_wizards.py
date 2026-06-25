from odoo import models, fields


class ClientOnboardingWizard(models.TransientModel):
    _name = "security.client.onboarding.wizard"
    _description = "Onboard New Client"

    partner_id = fields.Many2one(
        "res.partner", string="Client",
        domain=[("is_company", "=", True)], required=True,
    )
    site_name = fields.Char("Site Name", required=True)
    location = fields.Char("Location")
    supervisor_id = fields.Many2one("hr.employee", string="Site Supervisor")

    def action_create_site(self):
        site = self.env["security.client.site"].create({
            "name": self.site_name,
            "partner_id": self.partner_id.id,
            "location": self.location or False,
            "supervisor_id": self.supervisor_id.id if self.supervisor_id else False,
        })
        return {
            "type": "ir.actions.act_window",
            "res_model": "security.client.site",
            "res_id": site.id,
            "views": [[False, "form"]],
            "target": "current",
        }


class RosterSetupWizard(models.TransientModel):
    _name = "security.roster.setup.wizard"
    _description = "Roster Setup Check"

    site_id = fields.Many2one("security.client.site", string="Site", required=True)
    date_from = fields.Date("From Date", required=True)
    date_to = fields.Date("To Date", required=True)
    check_result = fields.Text("Check Result", readonly=True)

    def action_check(self):
        reqs = self.env["security.shift.requirement"].search([
            ("site_id", "=", self.site_id.id), ("active", "=", True),
        ])
        posts = self.env["security.post"].search([
            ("site_id", "=", self.site_id.id), ("active", "=", True),
        ])
        lines = [
            f"Site: {self.site_id.name}",
            f"Active Posts: {len(posts)}",
            f"Active Shift Requirements: {len(reqs)}",
        ]
        if not posts:
            lines.append("\nWARNING: No active posts found. Create posts before generating a roster.")
        if not reqs:
            lines.append("\nWARNING: No shift requirements found. Define requirements before generating a roster.")
        if posts and reqs:
            lines.append("\nReady: This site has posts and shift requirements configured.")
        self.check_result = "\n".join(lines)
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "views": [[False, "form"]],
            "target": "new",
        }
