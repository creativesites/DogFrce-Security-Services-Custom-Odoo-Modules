from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SecurityDuplicateAuditWizard(models.TransientModel):
    _name = "security.duplicate.audit.wizard"
    _description = "Duplicate Detection and Normalization Wizard"

    name = fields.Char(default="Duplicate Normalization Audit", required=True)
    line_ids = fields.One2many(
        "security.duplicate.audit.line",
        "wizard_id",
        string="Detected Candidate Records",
    )
    total_detected = fields.Integer(compute="_compute_counts", string="Total Candidates")
    approved_count = fields.Integer(compute="_compute_counts", string="Approved for Merge")

    @api.depends("line_ids", "line_ids.state")
    def _compute_counts(self):
        for wiz in self:
            wiz.total_detected = len(wiz.line_ids)
            wiz.approved_count = len(wiz.line_ids.filtered(lambda l: l.state == "approved"))

    def action_run_audit(self):
        """Dry-run detection of near-duplicate clients, sites, and invalid records."""
        self.ensure_one()
        self.line_ids.unlink()

        lines = []

        # 1. Near-duplicate clients
        partners = self.env["res.partner"].search([
            ("is_company", "=", True),
            ("active", "in", [True, False]),
        ])
        seen_partner_names = {}
        for p in partners:
            normalized = "".join(c.lower() for c in (p.name or "") if c.isalnum())
            if not normalized:
                continue
            if normalized in seen_partner_names:
                keeper = seen_partner_names[normalized]
                # Keep active over archived; keep older record (lower id)
                if not keeper.active and p.active:
                    keeper, duplicate = p, keeper
                    seen_partner_names[normalized] = p
                else:
                    duplicate = p
                lines.append({
                    "wizard_id": self.id,
                    "record_type": "client",
                    "keeper_partner_id": keeper.id,
                    "dup_partner_id": duplicate.id,
                    "reason": f"Near-identical client name ('{keeper.name}' vs '{duplicate.name}')",
                })
            else:
                seen_partner_names[normalized] = p

        # 2. Near-duplicate sites per client
        sites = self.env["security.client.site"].search([])
        sites_by_client = {}
        for s in sites:
            sites_by_client.setdefault(s.partner_id.id, []).append(s)

        for client_id, client_sites in sites_by_client.items():
            seen_site_names = {}
            for s in client_sites:
                norm_site = "".join(c.lower() for c in (s.name or "") if c.isalnum())
                if not norm_site:
                    continue
                if norm_site in seen_site_names:
                    keeper = seen_site_names[norm_site]
                    if not keeper.active and s.active:
                        keeper, duplicate = s, keeper
                        seen_site_names[norm_site] = s
                    else:
                        duplicate = s
                    lines.append({
                        "wizard_id": self.id,
                        "record_type": "site",
                        "keeper_site_id": keeper.id,
                        "dup_site_id": duplicate.id,
                        "reason": f"Near-identical site name under same client ('{keeper.name}' vs '{duplicate.name}')",
                    })
                else:
                    seen_site_names[norm_site] = s

        # 3. Numeric-only or obviously bad site records
        for s in sites:
            clean_name = (s.name or "").strip()
            if clean_name.isdigit() or len(clean_name) <= 1:
                lines.append({
                    "wizard_id": self.id,
                    "record_type": "site",
                    "dup_site_id": s.id,
                    "reason": f"Invalid/numeric-only site name ('{clean_name}')",
                })

        if lines:
            self.env["security.duplicate.audit.line"].create(lines)

        return {
            "type": "ir.actions.act_window",
            "res_model": "security.duplicate.audit.wizard",
            "res_id": self.id,
            "views": [[False, "form"]],
            "target": "new",
        }

    def action_merge_approved(self):
        """
        Merge approved candidate records.
        Preserves all history; never deletes records permanently.
        Archives duplicates and reassigns child links.
        """
        self.ensure_one()
        approved = self.line_ids.filtered(lambda l: l.state == "approved")
        if not approved:
            raise UserError(_("No candidates are approved for merge. Please review and approve candidates first."))

        merged_count = 0
        for line in approved:
            if line.record_type == "client" and line.keeper_partner_id and line.dup_partner_id:
                keeper = line.keeper_partner_id
                dup = line.dup_partner_id

                # Reassign sites
                self.env["security.client.site"].search([("partner_id", "=", dup.id)]).write({"partner_id": keeper.id})
                # Reassign contracts
                self.env["security.client.contract"].search([("partner_id", "=", dup.id)]).write({"partner_id": keeper.id})
                # Reassign roster batches
                self.env["security.roster.batch"].search([("partner_id", "=", dup.id)]).write({"partner_id": keeper.id})
                # Safe archive
                dup.write({"active": False})
                line.state = "merged"
                merged_count += 1

            elif line.record_type == "site" and line.dup_site_id:
                dup_site = line.dup_site_id
                keeper_site = line.keeper_site_id

                if keeper_site:
                    # Move posts to keeper site if not already existing
                    for post in dup_site.post_ids:
                        post.write({"site_id": keeper_site.id, "partner_id": keeper_site.partner_id.id})
                    # Move shift requirements
                    for req in dup_site.shift_requirement_ids:
                        req.write({"site_id": keeper_site.id})
                    # Move roster slots
                    self.env["security.roster.slot"].search([("site_id", "=", dup_site.id)]).write({"site_id": keeper_site.id})
                    # Move attendance records
                    if "security.attendance.record" in self.env:
                        self.env["security.attendance.record"].search([("site_id", "=", dup_site.id)]).write({"site_id": keeper_site.id})

                dup_site.write({"active": False})
                line.state = "merged"
                merged_count += 1

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Merge Complete"),
                "message": _("%d candidate record(s) safely merged and archived. Historical records preserved.") % merged_count,
                "type": "success",
            },
        }


class SecurityDuplicateAuditLine(models.TransientModel):
    _name = "security.duplicate.audit.line"
    _description = "Duplicate Audit Line"
    _order = "record_type, id"

    wizard_id = fields.Many2one("security.duplicate.audit.wizard", required=True, ondelete="cascade")
    record_type = fields.Selection([("client", "Client"), ("site", "Site")], required=True)
    keeper_partner_id = fields.Many2one("res.partner", string="Approved Keeper (Client)")
    dup_partner_id = fields.Many2one("res.partner", string="Duplicate (Client)")
    keeper_site_id = fields.Many2one("security.client.site", string="Approved Keeper (Site)")
    dup_site_id = fields.Many2one("security.client.site", string="Duplicate (Site)")
    reason = fields.Char(string="Diagnostic Reason")
    state = fields.Selection([
        ("detected", "Detected (Pending Review)"),
        ("approved", "Approved for Merge"),
        ("merged", "Merged & Archived"),
        ("skipped", "Skipped"),
    ], default="detected", required=True)

    def action_approve(self):
        self.write({"state": "approved"})

    def action_skip(self):
        self.write({"state": "skipped"})
