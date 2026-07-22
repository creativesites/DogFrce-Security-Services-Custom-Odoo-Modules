from datetime import date

from odoo import api, fields, models
from odoo.exceptions import ValidationError

STEPS = [
    ("1_client", "Client & Contract"),
    ("2_sites", "Sites"),
    ("3_requirements", "Shift Requirements"),
    ("4_billing", "Billing Plan"),
    ("5_roster", "First Roster"),
    ("6_confirm", "Confirm & Create"),
]
STEP_KEYS = [s[0] for s in STEPS]


class SecurityClientOnboardingWizard(models.TransientModel):
    _name = "security.client.onboarding.wizard"
    _description = "Client Onboarding Wizard"

    step = fields.Selection(STEPS, default="1_client", required=True, string="Step")

    # ── Step 1: Client & Contract ──────────────────────────────────────
    # Use either an existing client or create a new one
    existing_partner_id = fields.Many2one(
        "res.partner",
        string="Existing Client",
        help="Select if the client already exists in the system.",
    )
    new_partner_name = fields.Char("New Client Name")
    new_partner_email = fields.Char("Email")
    new_partner_phone = fields.Char("Phone")
    new_partner_street = fields.Char("Address")
    contract_start = fields.Date("Contract Start", default=fields.Date.today)

    # ── Step 2: Sites ──────────────────────────────────────────────────
    site_line_ids = fields.One2many(
        "security.client.onboarding.site",
        "wizard_id",
        string="Sites",
    )

    # ── Step 3: Shift Requirements ─────────────────────────────────────
    requirement_line_ids = fields.One2many(
        "security.client.onboarding.requirement",
        "wizard_id",
        string="Shift Requirements",
    )

    # ── Step 4: Billing Plan ───────────────────────────────────────────
    billing_mode = fields.Selection(
        [
            ("fixed_monthly", "Fixed Monthly Rate"),
            ("per_shift", "Per Shift"),
            ("per_hour", "Per Hour"),
            ("milestone", "Milestone"),
        ],
        string="Billing Mode",
        default="fixed_monthly",
    )
    billing_start = fields.Date("Billing Start", default=fields.Date.today)
    billing_payment_term_days = fields.Integer("Payment Term (days)", default=30)
    billing_vat_rate = fields.Float("VAT Rate (%)", default=15.0)

    # ── Step 5: First Roster ───────────────────────────────────────────
    generate_first_roster = fields.Boolean(
        "Generate First Roster Batch",
        default=True,
        help="Automatically generate roster slots for the first month.",
    )
    roster_month = fields.Date(
        "Roster Month (1st of month)",
        default=lambda self: date.today().replace(day=1),
    )

    # ── Step 6: Confirm ────────────────────────────────────────────────
    summary_html = fields.Html(
        compute="_compute_summary_html",
        string="Summary",
    )

    @api.depends(
        "existing_partner_id", "new_partner_name",
        "site_line_ids", "requirement_line_ids",
        "billing_mode", "generate_first_roster", "roster_month",
    )
    def _compute_summary_html(self):
        for wiz in self:
            client = (
                wiz.existing_partner_id.name
                if wiz.existing_partner_id
                else (wiz.new_partner_name or "—")
            )
            sites = len(wiz.site_line_ids)
            reqs = len(wiz.requirement_line_ids)
            roster_info = (
                f"Generate batch for {wiz.roster_month.strftime('%B %Y')}"
                if wiz.generate_first_roster and wiz.roster_month
                else "Skip"
            )
            wiz.summary_html = f"""
            <table class="table table-sm table-borderless mb-0">
                <tr><th style="width:40%">Client</th><td>{client}</td></tr>
                <tr><th>Contract Start</th><td>{wiz.contract_start or '—'}</td></tr>
                <tr><th>Sites</th><td>{sites} site(s)</td></tr>
                <tr><th>Shift Requirements</th><td>{reqs} requirement(s)</td></tr>
                <tr><th>Billing Mode</th><td>{dict(wiz._fields['billing_mode'].selection).get(wiz.billing_mode or 'fixed_monthly', '—')}</td></tr>
                <tr><th>First Roster</th><td>{roster_info}</td></tr>
            </table>
            """

    def _get_or_create_partner(self):
        if self.existing_partner_id:
            return self.existing_partner_id
        if not self.new_partner_name:
            raise ValidationError("Please enter a client name or select an existing client.")
        return self.env["res.partner"].create({
            "name": self.new_partner_name,
            "email": self.new_partner_email or False,
            "phone": self.new_partner_phone or False,
            "street": self.new_partner_street or False,
            "is_company": True,
        })

    def action_next(self):
        self.ensure_one()
        current_idx = STEP_KEYS.index(self.step)
        if current_idx < len(STEP_KEYS) - 1:
            self.step = STEP_KEYS[current_idx + 1]
        return self._reopen()

    def action_back(self):
        self.ensure_one()
        current_idx = STEP_KEYS.index(self.step)
        if current_idx > 0:
            self.step = STEP_KEYS[current_idx - 1]
        return self._reopen()

    def action_confirm(self):
        self.ensure_one()

        partner = self._get_or_create_partner()

        # Create sites
        sites = []
        for line in self.site_line_ids:
            site = self.env["security.client.site"].create({
                "name": line.site_name,
                "partner_id": partner.id,
                "location": line.location or False,
                "code": line.code or False,
            })
            sites.append(site)

        # Create shift requirements (link to site by sequence / site_name match)
        for req_line in self.requirement_line_ids:
            site = next(
                (s for s in sites if s.name == req_line.site_name),
                sites[0] if sites else False,
            )
            if not site:
                continue
            self.env["security.shift.requirement"].create({
                "site_id": site.id,
                "post_id": req_line.post_id.id if req_line.post_id else False,
                "shift_template_id": req_line.shift_template_id.id if req_line.shift_template_id else False,
                "guard_count": req_line.guard_count,
                "bill_rate": req_line.bill_rate,
                "pay_rate": req_line.pay_rate,
            })

        # Create billing plan
        billing_plan = self.env["security.billing.plan"].create({
            "name": f"{partner.name} — Billing Plan",
            "partner_id": partner.id,
            "billing_mode": self.billing_mode or "fixed_monthly",
            "date_start": self.billing_start or self.contract_start or fields.Date.today(),
            "payment_term_days": self.billing_payment_term_days,
            "vat_rate": self.billing_vat_rate,
            "active": True,
        })

        # Generate first roster batch
        batch = False
        if self.generate_first_roster and self.roster_month and sites:
            batch = self.env["security.roster.batch"].create({
                "name": f"{partner.name} — {self.roster_month.strftime('%B %Y')}",
                "partner_id": partner.id,
                "month": self.roster_month,
                "state": "draft",
            })

        # Navigate to the new client (partner)
        return {
            "type": "ir.actions.act_window",
            "res_model": "res.partner",
            "res_id": partner.id,
            "views": [[False, "form"]],
            "target": "current",
        }

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "security.client.onboarding.wizard",
            "res_id": self.id,
            "views": [[False, "form"]],
            "target": "new",
        }


class SecurityClientOnboardingSite(models.TransientModel):
    _name = "security.client.onboarding.site"
    _description = "Onboarding Wizard — Site Line"
    _order = "sequence"

    wizard_id = fields.Many2one(
        "security.client.onboarding.wizard",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    site_name = fields.Char("Site Name", required=True)
    code = fields.Char("Code", size=10)
    location = fields.Char("Address / Location")


class SecurityClientOnboardingRequirement(models.TransientModel):
    _name = "security.client.onboarding.requirement"
    _description = "Onboarding Wizard — Shift Requirement Line"
    _order = "sequence"

    wizard_id = fields.Many2one(
        "security.client.onboarding.wizard",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    site_name = fields.Char(
        "Site",
        help="Must match a site name entered in Step 2. Leave blank to use the first site.",
    )
    post_id = fields.Many2one("security.post", string="Post")
    shift_template_id = fields.Many2one("security.shift.template", string="Shift Template")
    guard_count = fields.Integer("Guard Count", default=1)
    bill_rate = fields.Float("Bill Rate (N$)", default=0.0)
    pay_rate = fields.Float("Pay Rate (N$)", default=0.0)


# ──────────────────────────────────────────────────────────────────────────────
# Roster Setup Health Check Wizard
# ──────────────────────────────────────────────────────────────────────────────

class SecurityRosterSetupWizard(models.TransientModel):
    _name = "security.roster.setup.wizard"
    _description = "Roster Setup Health Check"

    issue_ids = fields.One2many(
        "security.roster.setup.issue",
        "wizard_id",
        string="Issues Found",
    )
    issue_count = fields.Integer(compute="_compute_issue_count")

    @api.depends("issue_ids")
    def _compute_issue_count(self):
        for wiz in self:
            wiz.issue_count = len(wiz.issue_ids)

    def action_run_check(self):
        self.ensure_one()
        # Clear previous results
        self.issue_ids.unlink()

        checks = []

        # 1 — Active sites without any shift requirements
        sites = self.env["security.client.site"].search([("active", "=", True)])
        for site in sites:
            if not site.shift_requirement_ids.filtered("active"):
                checks.append({
                    "category": "sites",
                    "severity": "warning",
                    "title": f"'{site.name}' has no active shift requirements",
                })

        # 2 — Active shift requirements missing shift template or zero rates
        reqs = self.env["security.shift.requirement"].search([("active", "=", True)])
        for req in reqs:
            label = f"'{req.site_id.name}' / {req.post_id.name or 'no post'}"
            if not req.shift_template_id:
                checks.append({
                    "category": "requirements",
                    "severity": "warning",
                    "title": f"{label} — shift template not set",
                })
            if req.bill_rate == 0:
                checks.append({
                    "category": "billing",
                    "severity": "warning",
                    "title": f"{label} — bill rate is zero",
                })
            if req.pay_rate == 0:
                checks.append({
                    "category": "payroll",
                    "severity": "warning",
                    "title": f"{label} — pay rate is zero",
                })

        # 3 — Check current-month roster batches
        today = date.today()
        month_start = today.replace(day=1)
        current_batches = self.env["security.roster.batch"].search([
            ("date_from", ">=", month_start),
        ])
        if not current_batches:
            checks.append({
                "category": "roster",
                "severity": "critical",
                "title": f"No roster batch exists for {today.strftime('%B %Y')}",
            })
        else:
            # 4 — Unassigned slots in current month
            unassigned = self.env["security.roster.slot"].search([
                ("batch_id", "in", current_batches.ids),
                ("state", "not in", ["cancelled"]),
                ("employee_id", "=", False),
            ])
            if unassigned:
                checks.append({
                    "category": "roster",
                    "severity": "warning",
                    "title": f"{len(unassigned)} unassigned slot(s) in current month's roster",
                })

            # 5 — Draft batches that haven't been confirmed
            draft = current_batches.filtered(lambda b: b.state == "draft")
            if draft:
                checks.append({
                    "category": "roster",
                    "severity": "warning",
                    "title": f"{len(draft)} roster batch(es) still in Draft — not yet confirmed",
                })

        # 6 — Active clients without an active billing plan
        client_ids = sites.mapped("partner_id").ids
        for client_id in client_ids:
            bp = self.env["security.billing.plan"].search(
                [("partner_id", "=", client_id), ("active", "=", True)], limit=1
            )
            if not bp:
                partner = self.env["res.partner"].browse(client_id)
                checks.append({
                    "category": "billing",
                    "severity": "critical",
                    "title": f"Client '{partner.name}' has no active billing plan",
                })

        # 7 — Shift templates: confirm at least one exists
        if not self.env["security.shift.template"].search([], limit=1):
            checks.append({
                "category": "requirements",
                "severity": "critical",
                "title": "No shift templates defined — roster generation will not work",
            })

        for item in checks:
            self.env["security.roster.setup.issue"].create({
                "wizard_id": self.id,
                **item,
            })

        return self._reopen()

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "security.roster.setup.wizard",
            "res_id": self.id,
            "views": [[False, "form"]],
            "target": "new",
        }


class SecurityRosterSetupIssue(models.TransientModel):
    _name = "security.roster.setup.issue"
    _description = "Roster Setup Issue"
    _order = "severity desc, category, title"

    wizard_id = fields.Many2one(
        "security.roster.setup.wizard",
        required=True,
        ondelete="cascade",
    )
    severity = fields.Selection(
        [("critical", "Critical"), ("warning", "Warning")],
        required=True,
        default="warning",
    )
    category = fields.Char("Area")
    title = fields.Char("Issue", required=True)
