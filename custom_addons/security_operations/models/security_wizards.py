from odoo import models, fields, api


class ClientOnboardingWizard(models.TransientModel):
    _name = "security.client.onboarding.wizard"
    _description = "Onboard New Client"

    step = fields.Selection(
        [
            ("client", "1. Client"),
            ("site", "2. Site Details"),
            ("posts", "3. Posts"),
            ("requirements", "4. Requirements"),
            ("generate", "5. Generate Roster"),
        ],
        default="client",
        required=True,
        string="Step",
    )

    # Step 1 — Client
    partner_id = fields.Many2one(
        "res.partner", string="Client",
        domain=[("is_company", "=", True)],
    )

    # Step 2 — Site
    site_name = fields.Char("Site Name")
    location = fields.Char("Location")
    supervisor_id = fields.Many2one("hr.employee", string="Site Supervisor")
    site_id = fields.Many2one(
        "security.client.site", string="Created Site", readonly=True,
    )

    # Step 3/4 — counts (display only)
    post_count = fields.Integer("Posts Configured", readonly=True)
    requirement_count = fields.Integer("Requirements Configured", readonly=True)

    # Step 5 — Roster generation
    batch_date_from = fields.Date("Roster From")
    batch_date_to = fields.Date("Roster To")

    # ── Navigation helpers ──────────────────────────────────────────────

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "views": [[False, "form"]],
            "target": "new",
        }

    # ── Step 1 → 2 ──────────────────────────────────────────────────────

    def action_go_to_site(self):
        self.ensure_one()
        if not self.partner_id:
            raise models.ValidationError("Please select a client before continuing.")
        self.step = "site"
        return self._reopen()

    # ── Step 2 → 3 (creates site) ───────────────────────────────────────

    def action_create_site_and_continue(self):
        self.ensure_one()
        if not self.site_name:
            raise models.ValidationError("Site name is required.")
        site = self.env["security.client.site"].create({
            "name": self.site_name,
            "partner_id": self.partner_id.id,
            "location": self.location or False,
            "supervisor_id": self.supervisor_id.id if self.supervisor_id else False,
        })
        self.site_id = site.id
        self.step = "posts"
        return self._reopen()

    # ── Step 3 → 4 ──────────────────────────────────────────────────────

    def action_go_to_requirements(self):
        self.ensure_one()
        if self.site_id:
            self.post_count = self.env["security.post"].search_count([
                ("site_id", "=", self.site_id.id), ("active", "=", True),
            ])
        self.step = "requirements"
        return self._reopen()

    def action_open_posts(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "security.post",
            "views": [[False, "list"], [False, "form"]],
            "domain": [("site_id", "=", self.site_id.id)] if self.site_id else [],
            "context": {"default_site_id": self.site_id.id} if self.site_id else {},
            "target": "current",
        }

    # ── Step 4 → 5 ──────────────────────────────────────────────────────

    def action_go_to_generate(self):
        self.ensure_one()
        if self.site_id:
            self.requirement_count = self.env["security.shift.requirement"].search_count([
                ("site_id", "=", self.site_id.id), ("active", "=", True),
            ])
        self.step = "generate"
        return self._reopen()

    def action_open_requirements(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "security.shift.requirement",
            "views": [[False, "list"], [False, "form"]],
            "domain": [("site_id", "=", self.site_id.id)] if self.site_id else [],
            "context": {"default_site_id": self.site_id.id} if self.site_id else {},
            "target": "current",
        }

    # ── Step 5 — generate ───────────────────────────────────────────────

    def action_generate_roster(self):
        self.ensure_one()
        if not self.batch_date_from or not self.batch_date_to:
            raise models.ValidationError("Please select a date range for the roster.")
        batch = self.env["security.roster.batch"].create({
            "date_from": self.batch_date_from,
            "date_to": self.batch_date_to,
            "site_id": self.site_id.id if self.site_id else False,
            "partner_id": self.partner_id.id,
        })
        batch.action_generate_slots()
        return {
            "type": "ir.actions.act_window",
            "res_model": "security.roster.batch",
            "res_id": batch.id,
            "views": [[False, "form"]],
            "target": "current",
        }

    # ── Back navigation ─────────────────────────────────────────────────

    def action_back(self):
        self.ensure_one()
        steps = ["client", "site", "posts", "requirements", "generate"]
        idx = steps.index(self.step)
        if idx > 0:
            self.step = steps[idx - 1]
        return self._reopen()

    # ── Legacy single-step action (kept for backwards compat) ───────────

    def action_create_site(self):
        return self.action_create_site_and_continue()


class RosterSetupWizard(models.TransientModel):
    _name = "security.roster.setup.wizard"
    _description = "Roster Setup Check"

    site_id = fields.Many2one("security.client.site", string="Site", required=True)
    date_from = fields.Date("From Date", required=True)
    date_to = fields.Date("To Date", required=True)
    check_result = fields.Text("Check Result", readonly=True)

    def action_check(self):
        today = fields.Date.today()
        reqs = self.env["security.shift.requirement"].search([
            ("site_id", "=", self.site_id.id), ("active", "=", True),
        ])
        posts = self.env["security.post"].search([
            ("site_id", "=", self.site_id.id), ("active", "=", True),
        ])
        guards = self.env["hr.employee"].search([
            ("security_guard", "=", True),
            ("active", "=", True),
            ("security_disqualified", "=", False),
        ])
        contract_model = self.env.get("security.client.contract")
        contract = contract_model and contract_model.get_active_for_site(self.site_id, today)

        lines = [
            f"Site: {self.site_id.name}",
            f"Active Posts: {len(posts)}",
            f"Active Shift Requirements: {len(reqs)}",
            f"Available Guards (system-wide): {len(guards)}",
        ]

        # Contract validation
        if not contract:
            lines.append("\n⚠ CONTRACT: No active contract for this site.")
        elif contract.date_end and (contract.date_end - today).days <= 30:
            days_left = (contract.date_end - today).days
            lines.append(f"\n⚠ CONTRACT: Expiring in {days_left} day(s) — {contract.name}.")
        else:
            lines.append(f"\n✓ CONTRACT: {contract.name} — active.")

        if not posts:
            lines.append("\n⚠ No active posts found. Create posts before generating a roster.")
        if not reqs:
            lines.append("\n⚠ No shift requirements found. Define requirements before generating a roster.")
        if posts and reqs:
            lines.append("\n✓ Posts and shift requirements are configured.")

        lines.append(
            "\n✓ Ready to generate roster." if (posts and reqs) else
            "\n✗ Fix the warnings above before generating."
        )
        self.check_result = "\n".join(lines)
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "views": [[False, "form"]],
            "target": "new",
        }
