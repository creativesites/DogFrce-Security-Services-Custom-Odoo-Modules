from datetime import date, timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SecurityRosterGenerateWizard(models.TransientModel):
    _name = "security.roster.generate.wizard"
    _description = "Monthly Roster Generation Wizard"

    date_from = fields.Date(required=True, string="From Date")
    date_to = fields.Date(required=True, string="To Date")
    site_ids = fields.Many2many(
        "security.client.site",
        string="Sites to Roster",
        required=True,
    )
    use_scoring_engine = fields.Boolean(
        default=True,
        string="Use AI Scoring Engine",
        help="If enabled, uses the guard scoring engine to suggest optimal assignments.",
    )
    batch_name = fields.Char(
        string="Batch Name",
        compute="_compute_batch_name",
        store=False,
    )
    preview_line_ids = fields.One2many(
        "security.roster.generate.wizard.preview",
        "wizard_id",
        string="Preview",
        readonly=True,
    )
    state = fields.Selection(
        [("draft", "Configure"), ("preview", "Preview"), ("done", "Done")],
        default="draft",
    )

    @api.depends("date_from", "date_to")
    def _compute_batch_name(self):
        for wiz in self:
            if wiz.date_from and wiz.date_to:
                wiz.batch_name = f"Roster {wiz.date_from} — {wiz.date_to}"
            else:
                wiz.batch_name = "New Roster"

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for wiz in self:
            if wiz.date_to and wiz.date_from and wiz.date_to < wiz.date_from:
                raise ValidationError("End date must be after start date.")

    def action_preview(self):
        self.ensure_one()
        self.preview_line_ids.unlink()
        req_model = self.env["security.shift.requirement"]

        lines = []
        for site in self.site_ids:
            requirements = req_model.search([("site_id", "=", site.id)])
            for req in requirements:
                current = self.date_from
                while current <= self.date_to:
                    lines.append({
                        "wizard_id": self.id,
                        "site_id": site.id,
                        "post_id": req.post_id.id if req.post_id else False,
                        "shift_date": current,
                        "shift_template_id": (
                            req.shift_template_id.id if req.shift_template_id else False
                        ),
                        "suggested_employee_id": False,
                    })
                    current += timedelta(days=1)
        self.env["security.roster.generate.wizard.preview"].create(lines)
        self.state = "preview"
        return {
            "type": "ir.actions.act_window",
            "res_model": "security.roster.generate.wizard",
            "res_id": self.id,
            "views": [[False, "form"]],
            "target": "new",
        }

    def action_confirm(self):
        self.ensure_one()
        batch = self.env["security.roster.batch"].create({
            "name": self.batch_name,
            "date_from": self.date_from,
            "date_to": self.date_to,
        })
        for line in self.preview_line_ids:
            if not line.post_id or not line.shift_template_id:
                continue
            slot_vals = {
                "batch_id": batch.id,
                "post_id": line.post_id.id,
                "shift_date": line.shift_date,
                "shift_template_id": line.shift_template_id.id,
                "state": "confirmed",
            }
            if line.suggested_employee_id:
                slot_vals["employee_id"] = line.suggested_employee_id.id
            self.env["security.roster.slot"].create(slot_vals)
        self.state = "done"
        return {
            "type": "ir.actions.act_window",
            "res_model": "security.roster.batch",
            "res_id": batch.id,
            "views": [[False, "form"]],
            "target": "current",
        }


class SecurityRosterGenerateWizardPreview(models.TransientModel):
    _name = "security.roster.generate.wizard.preview"
    _description = "Roster Wizard Preview Line"
    _order = "shift_date, site_id"

    wizard_id = fields.Many2one(
        "security.roster.generate.wizard", ondelete="cascade"
    )
    site_id = fields.Many2one("security.client.site")
    post_id = fields.Many2one("security.post")
    shift_date = fields.Date()
    shift_template_id = fields.Many2one("security.shift.template")
    suggested_employee_id = fields.Many2one(
        "hr.employee",
        domain="[('security_guard','=',True),('active','=',True)]",
        string="Assigned Guard",
    )
