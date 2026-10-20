from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class SecurityContractSite(models.Model):
    _name = "security.contract.site"
    _description = "Contract Site Line"
    _order = "sequence, id"

    contract_id = fields.Many2one(
        "security.client.contract",
        required=True,
        ondelete="cascade",
        index=True,
        string="Contract",
    )
    sequence = fields.Integer(default=10)
    site_id = fields.Many2one(
        "security.client.site",
        string="Linked Operational Site",
        ondelete="set null",
        help="The active operational site record managed by this contract line.",
    )
    name = fields.Char(required=True, string="Site Name")
    code = fields.Char(string="Site Code")
    location = fields.Char(string="Physical Location")
    site_type = fields.Selection(
        [
            ("mining", "Mining / Heavy Industrial"),
            ("industrial", "Factory / Warehouse"),
            ("commercial", "Commercial Office"),
            ("residential", "Residential Estate"),
            ("retail", "Retail / Mall"),
            ("embassy", "Embassy / High Security"),
            ("banking", "Banking / Financial"),
            ("healthcare", "Healthcare / Hospital"),
        ],
        string="Site Sector",
        default="commercial",
    )
    supervisor_id = fields.Many2one(
        "hr.employee",
        string="Site Supervisor",
        domain=[("security_guard", "=", True)],
    )
    contact_name = fields.Char("Primary Site Contact")
    contact_phone = fields.Char("Site Contact Phone")
    contact_email = fields.Char("Site Contact Email")
    note = fields.Text("Operational Notes")

    post_line_ids = fields.One2many(
        "security.contract.post",
        "contract_site_id",
        string="Posts",
    )
    requirement_line_ids = fields.One2many(
        "security.contract.shift.requirement",
        "contract_site_id",
        string="Shift Requirements",
    )

    contract_guard_pool_ids = fields.Many2many(
        "hr.employee",
        "sec_contract_site_guard_rel",
        "contract_site_id",
        "employee_id",
        string="Regular Site Guards",
        domain=[("security_guard", "=", True), ("active", "=", True)],
        help="Regular operational guard team defined under this contract site.",
    )
    guard_pool_mode = fields.Selection(
        [
            ("site_only", "Regular Site Pool Only"),
            ("site_then_relief", "Site Pool with Relief Fallback"),
        ],
        string="Guard Pool Mode",
        default="site_only",
        required=True,
    )

    post_count = fields.Integer(
        compute="_compute_counts",
        store=True,
        string="Posts Count",
    )
    requirement_count = fields.Integer(
        compute="_compute_counts",
        store=True,
        string="Requirements Count",
    )
    estimated_monthly_slots = fields.Integer(
        compute="_compute_counts",
        store=True,
        string="Estimated Monthly Slots",
    )
    readiness_state = fields.Selection(
        [
            ("ready", "Ready"),
            ("needs_setup", "Needs Setup"),
        ],
        compute="_compute_readiness",
        store=True,
        string="Setup Status",
    )
    issue_count = fields.Integer(
        compute="_compute_readiness",
        store=True,
        string="Setup Issues",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code"):
                # Auto-generate unique site code
                next_seq = self.env["ir.sequence"].next_by_code("security.contract.site")
                if not next_seq:
                    count = self.search_count([]) + 1
                    next_seq = f"SITE-{count:03d}"
                vals["code"] = next_seq
        return super().create(vals_list)

    @api.depends("post_line_ids", "requirement_line_ids", "requirement_line_ids.estimated_monthly_slots")
    def _compute_counts(self):
        for site in self:
            site.post_count = len(site.post_line_ids)
            site.requirement_count = len(site.requirement_line_ids)
            site.estimated_monthly_slots = sum(site.requirement_line_ids.mapped("estimated_monthly_slots"))

    @api.depends("post_line_ids", "requirement_line_ids", "supervisor_id", "post_line_ids.requirement_line_ids")
    def _compute_readiness(self):
        for site in self:
            issues = 0
            if not site.post_line_ids:
                issues += 1
            else:
                for post in site.post_line_ids:
                    if not post.requirement_line_ids:
                        issues += 1
            if not site.supervisor_id:
                issues += 1
            for req in site.requirement_line_ids:
                if req.guard_count <= 0 or not req.shift_template_id:
                    issues += 1
            site.issue_count = issues
            # We consider ready if it has posts and requirements (supervisor is a warning)
            has_posts = bool(site.post_line_ids)
            all_posts_have_reqs = has_posts and all(bool(p.requirement_line_ids) for p in site.post_line_ids)
            site.readiness_state = "ready" if (has_posts and all_posts_have_reqs and issues <= 1) else "needs_setup"

    def action_duplicate_site(self):
        """Duplicates this site setup (posts + requirements) under the same contract."""
        self.ensure_one()
        new_site = self.copy({
            "name": f"{self.name} (Copy)",
            "code": False,
            "site_id": False,
        })
        for post in self.post_line_ids:
            new_post = post.copy({
                "contract_site_id": new_site.id,
                "code": False,
                "post_id": False,
            })
            for req in post.requirement_line_ids:
                req.copy({
                    "contract_site_id": new_site.id,
                    "contract_post_id": new_post.id,
                    "requirement_id": False,
                })
        return {
            "type": "ir.actions.act_window",
            "res_model": "security.contract.site",
            "res_id": new_site.id,
            "view_mode": "form",
            "target": "current",
        }

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get("syncing_contract_site"):
            for cs in self:
                if cs.site_id and cs.site_id.exists():
                    sync_vals = {}
                    if "name" in vals:
                        sync_vals["name"] = cs.name
                    if "location" in vals:
                        sync_vals["location"] = cs.location
                    if "site_type" in vals:
                        sync_vals["site_type"] = cs.site_type
                    if "supervisor_id" in vals:
                        sync_vals["supervisor_id"] = cs.supervisor_id.id if cs.supervisor_id else False
                    if "contact_name" in vals:
                        sync_vals["contact_name"] = cs.contact_name
                    if "contact_phone" in vals:
                        sync_vals["contact_phone"] = cs.contact_phone
                    if "contact_email" in vals:
                        sync_vals["contact_email"] = cs.contact_email
                    if "note" in vals:
                        sync_vals["note"] = cs.note
                    if "contract_guard_pool_ids" in vals:
                        sync_vals["site_guard_pool_ids"] = [(6, 0, cs.contract_guard_pool_ids.ids)]
                    if "guard_pool_mode" in vals:
                        sync_vals["guard_pool_mode"] = cs.guard_pool_mode
                    if sync_vals:
                        cs.site_id.with_context(syncing_contract_site=True).write(sync_vals)
        return res
