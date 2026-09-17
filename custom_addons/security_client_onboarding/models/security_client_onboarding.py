from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError

STEPS = [
    ("1_client", "Client"),
    ("2_sites", "Sites"),
    ("3_requirements", "Shifts"),
    ("4_billing", "Billing"),
    ("5_confirm", "Review & Create"),
]
STEP_KEYS = [s[0] for s in STEPS]


class SecurityClientOnboardingWizard(models.TransientModel):
    """One path from "new client" to "ready to roster".

    See docs/ROSTERING_SIMPLIFICATION_PLAN.md. Before this rewrite the wizard
    had three usability defects and one crash:

    * Shift requirements were linked to sites by typing the site name so it
      matched Step 2 *exactly* -- the ambiguity the GM complained about.
      Requirements now point at the site line itself.
    * Requirements asked for a `security.post`, but a brand-new client has no
      posts, so there was nothing valid to pick. The wizard now asks for a post
      *type* (seeded by security_operations) and creates the post itself.
    * Nothing was validated until the final step, so mistakes surfaced late as
      raw exceptions. Each step now validates on the way out, with a message
      naming the row and what to do about it.
    * "Generate First Roster" (on by default) wrote `month` and `name` to
      security.roster.batch. `month` does not exist on that model and `name` is
      a stored computed field, while the required `date_from`/`date_to` were
      never set -- so confirming the wizard with the default options raised.
    """

    _name = "security.client.onboarding.wizard"
    _description = "Client Onboarding Wizard"

    step = fields.Selection(STEPS, default="1_client", required=True, string="Step")

    # ── Step 1: client ────────────────────────────────────────────────────
    existing_partner_id = fields.Many2one(
        "res.partner",
        string="Existing Client",
        domain=[("is_company", "=", True)],
        help="Pick a client that is already in the system, or leave this empty "
             "and fill in the new-client fields instead.",
    )
    new_partner_name = fields.Char("Client Name")
    new_partner_email = fields.Char("Email")
    new_partner_phone = fields.Char("Phone")
    new_partner_street = fields.Char("Address")
    contract_start = fields.Date("Contract Start", default=fields.Date.today)

    client_display_name = fields.Char(compute="_compute_client_display_name")

    # ── Step 2: sites ─────────────────────────────────────────────────────
    site_line_ids = fields.One2many(
        "security.client.onboarding.site", "wizard_id", string="Sites"
    )
    site_count = fields.Integer(compute="_compute_counts")

    # ── Step 3: shift requirements ────────────────────────────────────────
    requirement_line_ids = fields.One2many(
        "security.client.onboarding.requirement", "wizard_id", string="Shift Requirements"
    )
    requirement_count = fields.Integer(compute="_compute_counts")
    total_guards = fields.Integer(compute="_compute_counts", string="Guards per day")

    # ── Step 4: billing ───────────────────────────────────────────────────
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

    # ── Step 5: review ────────────────────────────────────────────────────
    generate_first_roster = fields.Boolean("Create the first roster batch", default=True)
    roster_month = fields.Date(
        "Roster Month",
        default=lambda self: date.today().replace(day=1),
        help="A draft roster batch is created covering this whole month. "
             "Slots are generated from the shift requirements above.",
    )
    summary_html = fields.Html(compute="_compute_summary_html", string="Summary")
    blocking_html = fields.Html(compute="_compute_summary_html", string="Needs attention")
    is_ready = fields.Boolean(compute="_compute_summary_html")

    # ── Computes ──────────────────────────────────────────────────────────

    @api.depends("existing_partner_id", "new_partner_name")
    def _compute_client_display_name(self):
        for wiz in self:
            wiz.client_display_name = (
                wiz.existing_partner_id.name or wiz.new_partner_name or ""
            )

    @api.depends("site_line_ids", "requirement_line_ids", "requirement_line_ids.guard_count")
    def _compute_counts(self):
        for wiz in self:
            wiz.site_count = len(wiz.site_line_ids)
            wiz.requirement_count = len(wiz.requirement_line_ids)
            wiz.total_guards = sum(wiz.requirement_line_ids.mapped("guard_count"))

    def _collect_problems(self):
        """Everything standing between this wizard and a working client.

        Returned as (step_key, message) so the UI can tell the user not just
        what is wrong but which step to go back to.
        """
        self.ensure_one()
        problems = []

        if not self.existing_partner_id and not self.new_partner_name:
            problems.append(("1_client", "Choose an existing client or enter a new client name."))

        if not self.site_line_ids:
            problems.append(("2_sites", "Add at least one site — this is where guards are deployed."))
        for line in self.site_line_ids:
            if not line.site_name:
                problems.append(("2_sites", "One of the sites has no name."))

        if not self.requirement_line_ids:
            problems.append((
                "3_requirements",
                "Add at least one shift requirement, otherwise there is nothing to roster.",
            ))
        for line in self.requirement_line_ids:
            label = line.display_label
            if not line.site_line_id:
                problems.append(("3_requirements", f"{label}: pick which site this shift is for."))
            if not line.post_type_id:
                problems.append(("3_requirements", f"{label}: pick a post type."))
            if not line.shift_template_id:
                problems.append(("3_requirements", f"{label}: pick a shift."))
            if line.guard_count < 1:
                problems.append(("3_requirements", f"{label}: guard count must be at least 1."))

        return problems

    def _collect_warnings(self):
        """Things worth saying out loud that must never block setup.

        Rates are the big one: zero rates mean billing and payroll are
        incomplete, but they are not a reason to stop somebody rostering.
        """
        self.ensure_one()
        warnings = []
        no_bill = self.requirement_line_ids.filtered(lambda r: not r.bill_rate)
        no_pay = self.requirement_line_ids.filtered(lambda r: not r.pay_rate)
        if no_bill:
            warnings.append(
                f"{len(no_bill)} shift requirement(s) have no bill rate — "
                "you can roster, but invoicing for them will be incomplete."
            )
        if no_pay:
            warnings.append(
                f"{len(no_pay)} shift requirement(s) have no pay rate — "
                "you can roster, but payroll for them will be incomplete."
            )
        return warnings

    @api.depends(
        "existing_partner_id", "new_partner_name", "contract_start",
        "site_line_ids", "requirement_line_ids", "requirement_line_ids.guard_count",
        "requirement_line_ids.bill_rate", "requirement_line_ids.pay_rate",
        "billing_mode", "generate_first_roster", "roster_month",
    )
    def _compute_summary_html(self):
        step_labels = dict(STEPS)
        for wiz in self:
            problems = wiz._collect_problems()
            wiz.is_ready = not problems

            if problems:
                items = "".join(
                    f"<li><strong>{step_labels.get(step, step)}:</strong> {msg}</li>"
                    for step, msg in problems
                )
                wiz.blocking_html = (
                    "<p class='mb-1'>Before this client can be created:</p>"
                    f"<ul class='mb-0 ps-3'>{items}</ul>"
                )
            else:
                warnings = wiz._collect_warnings()
                if warnings:
                    items = "".join(f"<li>{w}</li>" for w in warnings)
                    wiz.blocking_html = (
                        "<p class='mb-1'>Ready to create. Worth knowing:</p>"
                        f"<ul class='mb-0 ps-3'>{items}</ul>"
                    )
                else:
                    wiz.blocking_html = False

            roster_line = "No roster batch"
            if wiz.generate_first_roster and wiz.roster_month:
                roster_line = (
                    f"Draft batch for {wiz.roster_month.strftime('%B %Y')}"
                )

            rows = [
                ("Client", wiz.client_display_name or "—"),
                ("Contract start", str(wiz.contract_start or "—")),
                ("Sites", f"{wiz.site_count}"),
                ("Shift requirements", f"{wiz.requirement_count}"),
                ("Guards on duty per day", f"{wiz.total_guards}"),
                (
                    "Billing",
                    dict(wiz._fields["billing_mode"].selection).get(
                        wiz.billing_mode or "fixed_monthly", "—"
                    ),
                ),
                ("First roster", roster_line),
            ]
            body = "".join(
                f"<tr><th class='text-muted fw-normal' style='width:45%'>{k}</th>"
                f"<td class='fw-bold'>{v}</td></tr>"
                for k, v in rows
            )
            wiz.summary_html = (
                f"<table class='table table-sm table-borderless mb-0'>{body}</table>"
            )

    # ── Navigation ────────────────────────────────────────────────────────

    def _validate_step(self, step):
        """Block leaving a step only for problems belonging to that step."""
        messages = [msg for s, msg in self._collect_problems() if s == step]
        if messages:
            raise ValidationError("\n".join(f"• {m}" for m in messages))

    def action_next(self):
        self.ensure_one()
        self._validate_step(self.step)
        idx = STEP_KEYS.index(self.step)
        if idx < len(STEP_KEYS) - 1:
            self.step = STEP_KEYS[idx + 1]
        return self._reopen()

    def action_back(self):
        self.ensure_one()
        idx = STEP_KEYS.index(self.step)
        if idx > 0:
            self.step = STEP_KEYS[idx - 1]
        return self._reopen()

    def action_goto_step(self):
        """Jump straight to a step from the progress bar."""
        self.ensure_one()
        target = self.env.context.get("goto_step")
        if target in STEP_KEYS:
            self.step = target
        return self._reopen()

    # ── Creation ──────────────────────────────────────────────────────────

    def _get_or_create_partner(self):
        if self.existing_partner_id:
            return self.existing_partner_id
        return self.env["res.partner"].create({
            "name": self.new_partner_name,
            "email": self.new_partner_email or False,
            "phone": self.new_partner_phone or False,
            "street": self.new_partner_street or False,
            "is_company": True,
        })

    def _get_or_create_post(self, site, post_type):
        """One post per (site, post type). Requirements on the same site and
        type share it rather than creating duplicates."""
        Post = self.env["security.post"]
        existing = Post.search(
            [("site_id", "=", site.id), ("post_type_id", "=", post_type.id)], limit=1
        )
        if existing:
            return existing
        return Post.create({
            "name": post_type.name,
            "site_id": site.id,
            "partner_id": site.partner_id.id,
            "post_type_id": post_type.id,
        })

    def action_confirm(self):
        self.ensure_one()
        problems = self._collect_problems()
        if problems:
            raise ValidationError(
                "This client cannot be created yet:\n"
                + "\n".join(f"• {msg}" for _step, msg in problems)
            )

        partner = self._get_or_create_partner()

        # Sites, keyed by their wizard line so requirements resolve exactly --
        # no name matching.
        site_by_line = {}
        for line in self.site_line_ids:
            site_by_line[line.id] = self.env["security.client.site"].create({
                "name": line.site_name,
                "partner_id": partner.id,
                "location": line.location or False,
                "code": line.code or False,
            })

        for req in self.requirement_line_ids:
            site = site_by_line[req.site_line_id.id]
            post = self._get_or_create_post(site, req.post_type_id)
            self.env["security.shift.requirement"].create({
                "site_id": site.id,
                "post_id": post.id,
                "shift_template_id": req.shift_template_id.id,
                "guard_count": req.guard_count,
                "bill_rate": req.bill_rate,
                "pay_rate": req.pay_rate,
            })

        self.env["security.billing.plan"].create({
            "name": f"{partner.name} — Billing Plan",
            "partner_id": partner.id,
            "billing_mode": self.billing_mode or "fixed_monthly",
            "date_start": self.billing_start or self.contract_start or fields.Date.today(),
            "payment_term_days": self.billing_payment_term_days,
            "vat_rate": self.billing_vat_rate,
            "active": True,
        })

        batch = self.env["security.roster.batch"]
        if self.generate_first_roster and self.roster_month:
            month_start = self.roster_month.replace(day=1)
            month_end = month_start + relativedelta(months=1, days=-1)
            # `name` is computed and stored on this model, and `date_from` /
            # `date_to` are required -- see this class's docstring.
            batch = batch.create({
                "partner_id": partner.id,
                "date_from": month_start,
                "date_to": month_end,
                "state": "draft",
            })

        message = (
            f"{partner.name} is set up: {self.site_count} site(s), "
            f"{self.requirement_count} shift requirement(s)."
        )
        if batch:
            message += " A draft roster batch is ready to generate."

        return {
            "type": "ir.actions.act_window",
            "res_model": "res.partner",
            "res_id": partner.id,
            "views": [[False, "form"]],
            "target": "current",
            "context": {"onboarding_message": message},
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
    _order = "sequence, id"
    # So the Step 3 site picker shows the site's name rather than a record id.
    _rec_name = "site_name"

    wizard_id = fields.Many2one(
        "security.client.onboarding.wizard", required=True, ondelete="cascade"
    )
    sequence = fields.Integer(default=10)
    site_name = fields.Char("Site Name", required=True)
    code = fields.Char("Code", size=10)
    location = fields.Char("Address / Location")


class SecurityClientOnboardingRequirement(models.TransientModel):
    _name = "security.client.onboarding.requirement"
    _description = "Onboarding Wizard — Shift Requirement Line"
    _order = "sequence, id"

    wizard_id = fields.Many2one(
        "security.client.onboarding.wizard", required=True, ondelete="cascade"
    )
    sequence = fields.Integer(default=10)

    # Points at the site *line*, not a typed-in name. This is what removed the
    # "must match Step 2 exactly" ambiguity.
    site_line_id = fields.Many2one(
        "security.client.onboarding.site",
        string="Site",
        domain="[('wizard_id', '=', parent.id)]",
        required=True,
        ondelete="cascade",
    )
    post_type_id = fields.Many2one("security.post.type", string="Post Type", required=True)
    shift_template_id = fields.Many2one("security.shift.template", string="Shift", required=True)
    guard_count = fields.Integer("Guards", default=1, required=True)
    bill_rate = fields.Float("Bill Rate")
    pay_rate = fields.Float("Pay Rate")

    display_label = fields.Char(compute="_compute_display_label")

    @api.depends("site_line_id.site_name", "post_type_id.name")
    def _compute_display_label(self):
        for line in self:
            site = line.site_line_id.site_name or "Unassigned site"
            post = line.post_type_id.name or "no post type"
            line.display_label = f"{site} / {post}"


class SecurityRosterSetupWizard(models.TransientModel):
    _name = "security.roster.setup.wizard"
    _description = "Roster Setup Health Check"

    issue_ids = fields.One2many(
        "security.roster.setup.issue", "wizard_id", string="Issues Found"
    )
    issue_count = fields.Integer(compute="_compute_issue_count")

    @api.depends("issue_ids")
    def _compute_issue_count(self):
        for wiz in self:
            wiz.issue_count = len(wiz.issue_ids)

    def action_run_check(self):
        self.ensure_one()
        self.issue_ids.unlink()

        checks = []

        sites = self.env["security.client.site"].search([("active", "=", True)])
        for site in sites:
            if not site.shift_requirement_ids.filtered("active"):
                checks.append({
                    "category": "sites",
                    "severity": "warning",
                    "title": f"'{site.name}' has no active shift requirements",
                })

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

            draft = current_batches.filtered(lambda b: b.state == "draft")
            if draft:
                checks.append({
                    "category": "roster",
                    "severity": "warning",
                    "title": f"{len(draft)} roster batch(es) still in Draft — not yet generated",
                })

        for client_id in sites.mapped("partner_id").ids:
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

        if not self.env["security.shift.template"].search([], limit=1):
            checks.append({
                "category": "requirements",
                "severity": "critical",
                "title": "No shift templates defined — roster generation will not work",
            })

        for item in checks:
            self.env["security.roster.setup.issue"].create({"wizard_id": self.id, **item})

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
        "security.roster.setup.wizard", required=True, ondelete="cascade"
    )
    severity = fields.Selection(
        [("critical", "Critical"), ("warning", "Warning")], required=True, default="warning"
    )
    category = fields.Char("Area")
    title = fields.Char("Issue", required=True)
