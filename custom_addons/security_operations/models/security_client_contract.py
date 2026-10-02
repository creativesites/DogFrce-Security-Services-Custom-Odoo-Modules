import json
import logging
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SecurityClientContract(models.Model):
    _name = "security.client.contract"
    _description = "Security Client Contract"
    _order = "date_start desc"

    name = fields.Char(required=True, string="Contract Reference")
    partner_id = fields.Many2one(
        "res.partner",
        required=True,
        string="Client",
        domain="[('is_company', '=', True)]",
    )
    # Legacy backward-compatibility field:
    site_id = fields.Many2one(
        "security.client.site",
        string="Legacy Single Site",
        domain="[('partner_id', '=', partner_id)]",
        help="Legacy single-site field. Modern contracts configure multiple sites via Contract Sites.",
    )
    contract_site_ids = fields.One2many(
        "security.contract.site",
        "contract_id",
        string="Contract Sites",
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
    rate_line_ids = fields.One2many(
        "security.contract.rate",
        "contract_id",
        string="Rate Card",
    )
    note = fields.Text()

    # Computed Operational Summaries
    sites_count = fields.Integer(
        compute="_compute_summary_counts",
        store=True,
        string="Covered Sites",
    )
    posts_count = fields.Integer(
        compute="_compute_summary_counts",
        store=True,
        string="Total Posts",
    )
    requirements_count = fields.Integer(
        compute="_compute_summary_counts",
        store=True,
        string="Shift Requirements",
    )
    estimated_monthly_slots = fields.Integer(
        compute="_compute_summary_counts",
        store=True,
        string="Est. Monthly Slots",
    )

    readiness_pct = fields.Float(
        compute="_compute_setup_health",
        store=True,
        string="Setup Readiness (%)",
    )
    setup_issues_count = fields.Integer(
        compute="_compute_setup_health",
        store=True,
        string="Setup Issues Count",
    )
    setup_issues_json = fields.Text(
        compute="_compute_setup_health",
        string="Setup Diagnostics JSON",
    )

    @api.depends("contract_site_ids", "contract_site_ids.post_count",
                 "contract_site_ids.requirement_count", "contract_site_ids.estimated_monthly_slots")
    def _compute_summary_counts(self):
        for contract in self:
            contract.sites_count = len(contract.contract_site_ids)
            contract.posts_count = sum(contract.contract_site_ids.mapped("post_count"))
            contract.requirements_count = sum(contract.contract_site_ids.mapped("requirement_count"))
            contract.estimated_monthly_slots = sum(contract.contract_site_ids.mapped("estimated_monthly_slots"))

    @api.depends("partner_id", "date_start", "contract_site_ids",
                 "contract_site_ids.post_line_ids", "contract_site_ids.requirement_line_ids",
                 "contract_site_ids.supervisor_id", "rate_line_ids")
    def _compute_setup_health(self):
        for contract in self:
            diagnostics = contract._evaluate_setup_health()
            contract.readiness_pct = diagnostics["readiness_pct"]
            contract.setup_issues_count = len(diagnostics["issues"])
            contract.setup_issues_json = json.dumps(diagnostics)

    def _evaluate_setup_health(self):
        """Evaluate contract readiness with human-readable actionable items."""
        self.ensure_one()
        checks = []
        issues = []
        score = 0
        total_possible = 6

        # 1. Client configured
        if self.partner_id:
            score += 1
            checks.append({"id": "client", "title": "Client configured", "status": "pass"})
        else:
            issues.append({
                "id": "client_missing",
                "severity": "critical",
                "title": "Client not specified",
                "action": "Select a client for this contract before proceeding.",
                "tab": "overview",
            })
            checks.append({"id": "client", "title": "Client configured", "status": "fail"})

        # 2. Contract term
        if self.date_start:
            score += 1
            checks.append({"id": "term", "title": "Contract dates configured", "status": "pass"})
        else:
            issues.append({
                "id": "dates_missing",
                "severity": "critical",
                "title": "Start date missing",
                "action": "Specify the contract start date.",
                "tab": "overview",
            })
            checks.append({"id": "term", "title": "Contract dates configured", "status": "fail"})

        # 3. Sites configured
        sites = self.contract_site_ids
        if sites:
            score += 1
            checks.append({"id": "sites", "title": f"{len(sites)} site(s) configured", "status": "pass"})
        else:
            issues.append({
                "id": "sites_missing",
                "severity": "critical",
                "title": "No sites configured",
                "action": "Add at least one site covered by this contract.",
                "tab": "sites",
            })
            checks.append({"id": "sites", "title": "Sites configured", "status": "fail"})

        # 4. Posts configured
        posts = sites.mapped("post_line_ids")
        if sites and posts:
            score += 1
            checks.append({"id": "posts", "title": f"{len(posts)} post(s) positioned", "status": "pass"})
        elif sites:
            issues.append({
                "id": "posts_missing",
                "severity": "critical",
                "title": "Sites have no posts",
                "action": "Add post positions (e.g. Main Gate, Reception) to each covered site.",
                "tab": "sites",
            })
            checks.append({"id": "posts", "title": "Posts positioned", "status": "fail"})
        else:
            checks.append({"id": "posts", "title": "Posts positioned", "status": "pending"})

        # 5. Shift Requirements
        reqs = sites.mapped("requirement_line_ids")
        sites_without_reqs = [s.name for s in sites if not s.requirement_line_ids]
        if sites and reqs and not sites_without_reqs:
            score += 1
            checks.append({"id": "requirements", "title": f"{len(reqs)} shift requirement(s) active", "status": "pass"})
        elif sites_without_reqs:
            missing_names = ", ".join(sites_without_reqs[:2])
            issues.append({
                "id": "requirements_missing",
                "severity": "critical",
                "title": f"Shift requirements missing on {missing_names}",
                "action": f"{missing_names} has posts but no active shift requirements. Add at least one Day or Night shift.",
                "tab": "sites",
            })
            checks.append({"id": "requirements", "title": "Shift requirements configured", "status": "fail"})
        else:
            checks.append({"id": "requirements", "title": "Shift requirements configured", "status": "pending"})

        # 6. Operational checks (Supervisors, Rates)
        sites_without_super = [s.name for s in sites if not s.supervisor_id]
        if sites_without_super:
            issues.append({
                "id": "supervisors_missing",
                "severity": "attention",
                "title": f"Site '{sites_without_super[0]}' has no supervisor",
                "action": "Assign an active security supervisor to ensure daily posting and attendance can be supervised.",
                "tab": "sites",
            })
            checks.append({"id": "supervisors", "title": f"Missing supervisor on {len(sites_without_super)} site(s)", "status": "warn"})
        elif sites:
            checks.append({"id": "supervisors", "title": "Site supervisors assigned", "status": "pass"})

        # Rates check
        if self.rate_line_ids:
            score += 1
            checks.append({"id": "rates", "title": "Contract rate card configured", "status": "pass"})
        else:
            issues.append({
                "id": "rate_card_empty",
                "severity": "watch",
                "title": "Contract rate card empty",
                "action": "Configure default billing rates on the Rate Card to auto-calculate planned revenue.",
                "tab": "rates",
            })
            checks.append({"id": "rates", "title": "Rate card configured", "status": "warn"})

        pct = round((score / float(total_possible)) * 100, 1)
        return {
            "readiness_pct": pct,
            "score": score,
            "total_possible": total_possible,
            "checks": checks,
            "issues": issues,
        }

    def _compute_billing_cap(self):
        today = date.today()
        first_day = today.replace(day=1)
        attendance_model = self.env.get("security.attendance.record")
        for contract in self:
            billed = 0.0
            site_ids = contract.contract_site_ids.mapped("site_id.id")
            if contract.site_id and contract.site_id.id not in site_ids:
                site_ids.append(contract.site_id.id)

            if attendance_model and site_ids:
                records = attendance_model.search([
                    ("site_id", "in", site_ids),
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

    def get_rate_for(self, grade, shift_category):
        """Return agreed hourly rate for the grade and category."""
        self.ensure_one()
        lines = self.rate_line_ids
        grade_id = grade.id if grade else None

        def _match(cat, gid):
            for line in lines:
                if line.shift_category != cat:
                    continue
                line_gid = line.grade_id.id if line.grade_id else None
                if line_gid == gid:
                    return line.hourly_rate
            return None

        if grade_id:
            r = _match(shift_category, grade_id)
            if r is not None:
                return r
        r = _match(shift_category, None)
        if r is not None:
            return r
        if grade_id and shift_category != "normal":
            r = _match("normal", grade_id)
            if r is not None:
                return r
        if shift_category != "normal":
            r = _match("normal", None)
            if r is not None:
                return r
        return 0.0

    def get_active_for_site(self, site, target_date):
        """Return active contract covering the site on target_date."""
        contracts = self.search([
            ("partner_id", "=", site.partner_id.id),
            ("state", "=", "active"),
            ("date_start", "<=", target_date),
            "|",
            ("date_end", "=", False),
            ("date_end", ">=", target_date),
        ])
        # 1. Multi-site contract covering this site
        multi_site = contracts.filtered(
            lambda c: site.id in c.contract_site_ids.mapped("site_id.id")
        )
        if multi_site:
            return multi_site[0]
        # 2. Legacy single-site contract
        single = contracts.filtered(lambda c: c.site_id == site)
        if single:
            return single[0]
        # 3. Client-wide contract
        client_wide = contracts.filtered(lambda c: not c.site_id and not c.contract_site_ids)
        if client_wide:
            return client_wide[0]
        return self.browse()

    def action_activate(self):
        """
        Atomic contract activation.
        Synchronizes contract sites, posts, and shift requirements into active operational records.
        Rolls back completely if any validation or sync error occurs.
        """
        for contract in self:
            diagnostics = contract._evaluate_setup_health()
            critical_issues = [i for i in diagnostics["issues"] if i.get("severity") == "critical"]
            if critical_issues:
                issue_bullets = "\n".join(f"• {i['title']}: {i['action']}" for i in critical_issues)
                raise UserError(
                    f"Contract '{contract.name}' cannot be activated yet:\n\n{issue_bullets}"
                )

            # Atomic sync of sites, posts, and requirements
            created_sites = 0
            created_posts = 0
            created_reqs = 0

            site_model = self.env["security.client.site"]
            post_model = self.env["security.post"]
            req_model = self.env["security.shift.requirement"]

            for c_site in contract.contract_site_ids:
                # 1. Sync or Create Site
                operational_site = c_site.site_id
                if not operational_site or not operational_site.exists():
                    operational_site = site_model.create({
                        "name": c_site.name,
                        "code": c_site.code,
                        "partner_id": contract.partner_id.id,
                        "location": c_site.location,
                        "site_type": c_site.site_type,
                        "supervisor_id": c_site.supervisor_id.id if c_site.supervisor_id else False,
                        "contact_name": c_site.contact_name,
                        "contact_phone": c_site.contact_phone,
                        "contact_email": c_site.contact_email,
                        "note": c_site.note,
                        "contract_id": contract.id,
                        "is_contract_managed": True,
                    })
                    c_site.site_id = operational_site.id
                    created_sites += 1
                else:
                    operational_site.write({
                        "name": c_site.name,
                        "location": c_site.location,
                        "site_type": c_site.site_type,
                        "supervisor_id": c_site.supervisor_id.id if c_site.supervisor_id else False,
                        "contact_name": c_site.contact_name,
                        "contact_phone": c_site.contact_phone,
                        "contact_email": c_site.contact_email,
                        "contract_id": contract.id,
                        "is_contract_managed": True,
                    })

                # 2. Sync or Create Posts
                for c_post in c_site.post_line_ids:
                    operational_post = c_post.post_id
                    if not operational_post or not operational_post.exists():
                        operational_post = post_model.create({
                            "name": c_post.name,
                            "code": c_post.code,
                            "site_id": operational_site.id,
                            "partner_id": contract.partner_id.id,
                            "post_type_id": c_post.post_type_id.id if c_post.post_type_id else False,
                            "required_guard_count": c_post.required_guard_count or 1,
                            "contract_post_id": c_post.id,
                            "is_contract_managed": True,
                        })
                        c_post.post_id = operational_post.id
                        created_posts += 1
                    else:
                        operational_post.write({
                            "name": c_post.name,
                            "required_guard_count": c_post.required_guard_count or 1,
                            "contract_post_id": c_post.id,
                            "is_contract_managed": True,
                        })

                    # 3. Sync or Create Requirements
                    for c_req in c_post.requirement_line_ids:
                        operational_req = c_req.requirement_id
                        req_vals = {
                            "site_id": operational_site.id,
                            "post_id": operational_post.id,
                            "shift_template_id": c_req.shift_template_id.id,
                            "guard_count": c_req.guard_count,
                            "monday": c_req.monday,
                            "tuesday": c_req.tuesday,
                            "wednesday": c_req.wednesday,
                            "thursday": c_req.thursday,
                            "friday": c_req.friday,
                            "saturday": c_req.saturday,
                            "sunday": c_req.sunday,
                            "bill_rate": c_req.bill_rate,
                            "pay_rate": c_req.pay_rate,
                            "rate_multiplier": c_req.rate_multiplier,
                            "fairness_weight": c_req.fairness_weight,
                            "preferred_employee_id": c_req.preferred_employee_id.id if c_req.preferred_employee_id else False,
                            "allow_preferred_only": c_req.allow_preferred_only,
                            "required_certification_ids": [(6, 0, c_req.required_certification_ids.ids)],
                            "required_language_ids": [(6, 0, c_req.required_language_ids.ids)],
                            "required_attribute_ids": [(6, 0, c_req.required_attribute_ids.ids)],
                            "contract_requirement_id": c_req.id,
                            "is_contract_managed": True,
                        }
                        if not operational_req or not operational_req.exists():
                            operational_req = req_model.create(req_vals)
                            c_req.requirement_id = operational_req.id
                            created_reqs += 1
                        else:
                            operational_req.write(req_vals)

            contract.state = "active"
            msg = (
                f"Contract activated. Operational setup synchronized: "
                f"{len(contract.contract_site_ids)} site(s), "
                f"{contract.posts_count} post(s), "
                f"{contract.requirements_count} requirement(s)."
            )
            if hasattr(contract, "message_post"):
                contract.message_post(body=msg)

            # Auto-generate operational roster batch for active cycle
            try:
                batch_model = self.env["security.roster.batch"] if "security.roster.batch" in self.env else None
                if batch_model:
                    batch_model.action_run_cycle_autoroster(cycle_type="current", contract_ids=[contract.id])
            except Exception as e:
                _logger.warning("Automated roster generation on contract %s activation notice: %s", contract.name, e)

        return True

    def action_trigger_auto_roster(self, cycle_type="current"):
        """Staff action to generate and auto-fill roster for this contract's sites."""
        self.ensure_one()
        batch_model = self.env["security.roster.batch"] if "security.roster.batch" in self.env else None
        if not batch_model:
            raise UserError("Roster batch system is not available.")
        return batch_model.action_run_cycle_autoroster(cycle_type=cycle_type, contract_ids=[self.id])

    def action_terminate(self):
        for contract in self:
            contract.state = "terminated"

    def action_reset_to_draft(self):
        for contract in self:
            contract.state = "draft"

    def action_open_contract_workspace(self):
        """Opens the OWL interactive Contract Workspace."""
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "security_operations.contract_workspace",
            "name": f"Contract Workspace — {self.name}",
            "context": {
                "active_id": self.id,
                "active_model": "security.client.contract",
            },
            "target": "current",
        }

    @api.model
    def get_cycle_dates_for(self, target_date=None):
        """
        Return the 21st-to-20th operational cycle (start_date, end_date) for target_date.
        If day >= 21: cycle runs from 21st of this month to 20th of next month.
        If day < 21: cycle runs from 21st of prev month to 20th of this month.
        """
        ref = target_date or date.today()
        if isinstance(ref, str):
            ref = fields.Date.from_string(ref)

        if ref.day >= 21:
            start_date = ref.replace(day=21)
            next_m = ref + relativedelta(months=1)
            end_date = next_m.replace(day=20)
        else:
            prev_m = ref - relativedelta(months=1)
            start_date = prev_m.replace(day=21)
            end_date = ref.replace(day=20)
        return start_date, end_date
