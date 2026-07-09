import calendar
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SecurityPostType(models.Model):
    _name = "security.post.type"
    _description = "Security Post Type"
    _order = "name"

    name = fields.Char(required=True)
    code = fields.Char()
    description = fields.Text()
    min_grade_id = fields.Many2one("security.grade", string="Minimum Grade")
    required_certification_ids = fields.Many2many(
        "security.certification",
        "security_post_type_certification_rel",
        "post_type_id",
        "certification_id",
        string="Required Certifications",
    )
    required_language_ids = fields.Many2many(
        "security.language",
        "security_post_type_language_rel",
        "post_type_id",
        "language_id",
        string="Required Languages",
    )
    required_attribute_ids = fields.Many2many(
        "security.attribute",
        "security_post_type_attribute_rel",
        "post_type_id",
        "attribute_id",
        string="Required Attributes",
    )
    minimum_reliability_score = fields.Integer(default=0)
    active = fields.Boolean(default=True)


class SecurityClientSite(models.Model):
    _name = "security.client.site"
    _description = "Security Client Site"
    _order = "partner_id, name"

    name = fields.Char(required=True)
    code = fields.Char()
    partner_id = fields.Many2one("res.partner", required=True, string="Client", domain=[("is_company", "=", True)])
    location = fields.Char()
    supervisor_id = fields.Many2one(
        "hr.employee",
        domain=[("security_guard", "=", True)],
    )
    active = fields.Boolean(default=True)
    post_ids = fields.One2many("security.post", "site_id", string="Post Positions")
    shift_requirement_ids = fields.One2many(
        "security.shift.requirement",
        "site_id",
        string="Shift Requirements",
    )
    exclusion_ids = fields.One2many(
        "security.guard.exclusion",
        "site_id",
        string="Guard Exclusions",
    )
    note = fields.Text()
    site_coverage_today = fields.Float(
        compute="_compute_site_coverage_today",
        string="Today's Coverage (%)",
    )
    site_coverage_month = fields.Float(
        compute="_compute_site_coverage_month",
        string="Month-to-Date Coverage (%)",
    )
    contract_status = fields.Selection(
        [
            ("valid", "Contract Valid"),
            ("expiring_soon", "Expiring Soon"),
            ("expired", "Expired"),
            ("none", "No Contract"),
        ],
        compute="_compute_contract_status",
        string="Contract Status",
    )
    risk_level = fields.Selection(
        [
            ("low", "Low Risk"),
            ("medium", "Medium Risk"),
            ("high", "High Risk"),
            ("critical", "Critical"),
        ],
        compute="_compute_risk_level",
        string="Risk Level",
    )

    def _compute_contract_status(self):
        today = fields.Date.today()
        contract_model = self.env.get("security.client.contract")
        for site in self:
            if not contract_model:
                site.contract_status = "none"
                continue
            contract = contract_model.get_active_for_site(site, today)
            if not contract:
                site.contract_status = "none"
            elif contract.date_end and (contract.date_end - today).days <= 30:
                site.contract_status = "expiring_soon"
            else:
                site.contract_status = "valid"
        # Mark expired contracts for sites with no active contract but a past one
        for site in self:
            if site.contract_status == "none" and contract_model:
                past = contract_model.search([
                    ("site_id", "=", site.id),
                    ("state", "in", ("active", "expired")),
                    ("date_end", "<", today),
                ], limit=1)
                if past:
                    site.contract_status = "expired"

    def _compute_risk_level(self):
        for site in self:
            today_cov = site.site_coverage_today
            month_cov = site.site_coverage_month
            if today_cov < 50 or month_cov < 60:
                site.risk_level = "critical"
            elif today_cov < 75 or month_cov < 75:
                site.risk_level = "high"
            elif today_cov < 90 or month_cov < 85:
                site.risk_level = "medium"
            else:
                site.risk_level = "low"

    def _compute_site_coverage_today(self):
        today = fields.Date.today()
        slot_model = self.env["security.roster.slot"]
        for site in self:
            slots = slot_model.search([
                ("site_id", "=", site.id),
                ("shift_date", "=", today),
                ("state", "!=", "cancelled"),
            ])
            total = len(slots)
            assigned = len(slots.filtered(
                lambda s: s.employee_id and s.state in ("assigned", "confirmed")
            ))
            site.site_coverage_today = (assigned / total * 100.0) if total else 0.0

    def _compute_site_coverage_month(self):
        today = fields.Date.today()
        first_day = today.replace(day=1)
        slot_model = self.env["security.roster.slot"]
        for site in self:
            slots = slot_model.search([
                ("site_id", "=", site.id),
                ("shift_date", ">=", first_day),
                ("shift_date", "<=", today),
                ("state", "!=", "cancelled"),
            ])
            total = len(slots)
            assigned = len(slots.filtered(
                lambda s: s.employee_id and s.state in ("assigned", "confirmed")
            ))
            site.site_coverage_month = (assigned / total * 100.0) if total else 0.0

    @api.model
    def get_calendar_data(self, site_id, month_str):
        year, month = map(int, month_str.split("-"))
        days_in_month = calendar.monthrange(year, month)[1]
        first_weekday = calendar.weekday(year, month, 1)

        date_from = date(year, month, 1)
        date_to = date(year, month, days_in_month)
        slots = self.env["security.roster.slot"].search([
            ("site_id", "=", site_id),
            ("shift_date", ">=", date_from),
            ("shift_date", "<=", date_to),
            ("state", "!=", "cancelled"),
        ])

        days_data = {}
        for slot in slots:
            key = str(slot.shift_date)
            if key not in days_data:
                days_data[key] = {"total": 0, "assigned": 0, "slots": []}
            days_data[key]["total"] += 1
            if slot.employee_id and slot.state in ("assigned", "confirmed"):
                days_data[key]["assigned"] += 1
            days_data[key]["slots"].append({
                "id": slot.id,
                "shift": slot.shift_template_id.name if slot.shift_template_id else "",
                "post": slot.post_id.name if slot.post_id else "",
                "guard": slot.employee_id.name if slot.employee_id else "",
            })

        return {
            "days_in_month": days_in_month,
            "first_weekday": first_weekday,
            "days": days_data,
        }

    # Live coverage stats (non-stored, computed on demand)
    site_coverage_today = fields.Float(
        compute="_compute_site_coverage",
        string="Coverage Today (%)",
    )
    site_coverage_month = fields.Float(
        compute="_compute_site_coverage",
        string="Coverage This Month (%)",
    )

    def _compute_site_coverage(self):
        today = fields.Date.today()
        month_start = today.replace(day=1)
        for site in self:
            today_slots = self.env["security.roster.slot"].search([
                ("site_id", "=", site.id),
                ("shift_date", "=", today),
                ("state", "!=", "cancelled"),
            ])
            site.site_coverage_today = (
                len(today_slots.filtered("employee_id")) / len(today_slots) * 100
                if today_slots else 0.0
            )
            month_slots = self.env["security.roster.slot"].search([
                ("site_id", "=", site.id),
                ("shift_date", ">=", month_start),
                ("shift_date", "<=", today),
                ("state", "!=", "cancelled"),
            ])
            site.site_coverage_month = (
                len(month_slots.filtered("employee_id")) / len(month_slots) * 100
                if month_slots else 0.0
            )

    @api.model
    def get_calendar_data(self, site_id, month=None):
        site = self.browse(site_id)
        if not site.exists():
            return {"error": "Site not found"}

        if month:
            year, m = map(int, month.split("-"))
        else:
            today = date.today()
            year, m = today.year, today.month

        days_in_month = calendar.monthrange(year, m)[1]
        month_start = date(year, m, 1)
        month_end = date(year, m, days_in_month)

        slots = self.env["security.roster.slot"].search([
            ("site_id", "=", site_id),
            ("shift_date", ">=", month_start),
            ("shift_date", "<=", month_end),
            ("state", "!=", "cancelled"),
        ])

        days = {}
        for slot in slots:
            d = str(slot.shift_date)
            if d not in days:
                days[d] = {"total": 0, "assigned": 0, "slots": []}
            days[d]["total"] += 1
            if slot.employee_id:
                days[d]["assigned"] += 1
            days[d]["slots"].append({
                "id": slot.id,
                "post": slot.post_id.name or "",
                "shift": slot.shift_template_id.name or "",
                "guard": slot.employee_id.name or "",
                "state": slot.state,
            })

        return {
            "site_id": site_id,
            "site_name": site.name,
            "year": year,
            "month": m,
            "days_in_month": days_in_month,
            "first_weekday": month_start.weekday(),
            "days": days,
        }

    def action_open_site_hub(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "security_operations.site_hub",
            "name": f"Site Hub — {self.name}",
            "context": {"active_id": self.id, "active_model": "security.client.site"},
            "target": "current",
        }


class SecurityPost(models.Model):
    _name = "security.post"
    _description = "Security Post"
    _order = "partner_id, site_id, name"

    name = fields.Char(required=True)
    code = fields.Char()
    active = fields.Boolean(default=True)
    site_id = fields.Many2one("security.client.site", string="Client Site", domain="[('partner_id','=',partner_id)]")
    partner_id = fields.Many2one(
        "res.partner",
        string="Client",
        domain=[("is_company", "=", True)],
    )
    post_type_id = fields.Many2one("security.post.type", required=True)
    location = fields.Char()
    required_guard_count = fields.Integer(default=1)
    shift_template_id = fields.Many2one(
        "security.shift.template",
        help="Legacy/default shift. Use shift requirements for multiple schedules.",
    )
    shift_requirement_ids = fields.One2many(
        "security.shift.requirement",
        "post_id",
        string="Shift Requirements",
    )
    note = fields.Text()

    @api.onchange("site_id")
    def _onchange_site_id(self):
        for post in self:
            if post.site_id:
                post.partner_id = post.site_id.partner_id

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        for post in self:
            if post.site_id and post.site_id.partner_id != post.partner_id:
                post.site_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("site_id") and not vals.get("partner_id"):
                vals["partner_id"] = self.env["security.client.site"].browse(vals["site_id"]).partner_id.id
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("site_id") and not vals.get("partner_id"):
            vals["partner_id"] = self.env["security.client.site"].browse(vals["site_id"]).partner_id.id
        return super().write(vals)


class SecurityShiftTemplate(models.Model):
    _name = "security.shift.template"
    _description = "Security Shift Template"
    _order = "name"

    name = fields.Char(required=True)
    start_hour = fields.Float(required=True, default=6.0)
    end_hour = fields.Float(required=True, default=18.0)
    duration_hours = fields.Float(
        compute="_compute_duration_hours",
        store=True,
    )
    active = fields.Boolean(default=True)
    note = fields.Text()

    @api.depends("start_hour", "end_hour")
    def _compute_duration_hours(self):
        for template in self:
            duration = template.end_hour - template.start_hour
            if duration <= 0:
                duration += 24.0
            template.duration_hours = duration


class SecurityShiftRequirement(models.Model):
    _name = "security.shift.requirement"
    _description = "Security Shift Requirement"
    _order = "site_id, post_id, shift_template_id"

    name = fields.Char(compute="_compute_name", store=True)
    site_id = fields.Many2one("security.client.site", required=True)
    partner_id = fields.Many2one(related="site_id.partner_id", store=True, string="Client")
    post_id = fields.Many2one("security.post", required=True)
    post_type_id = fields.Many2one(related="post_id.post_type_id", store=True)
    shift_template_id = fields.Many2one("security.shift.template", required=True)
    guard_count = fields.Integer(default=1, required=True)
    monday = fields.Boolean(default=True)
    tuesday = fields.Boolean(default=True)
    wednesday = fields.Boolean(default=True)
    thursday = fields.Boolean(default=True)
    friday = fields.Boolean(default=True)
    saturday = fields.Boolean(default=True)
    sunday = fields.Boolean(default=True)
    bill_rate = fields.Float(default=0.0)
    pay_rate = fields.Float(default=0.0)
    rate_multiplier = fields.Float(default=1.0)
    overtime_allowed = fields.Boolean(default=True)
    fairness_weight = fields.Float(
        default=1.0,
        help="Higher values identify shifts that should be balanced more carefully.",
    )
    minimum_reliability_score = fields.Integer(default=0)
    required_certification_ids = fields.Many2many(
        "security.certification",
        "security_shift_requirement_certification_rel",
        "requirement_id",
        "certification_id",
        string="Required Certifications",
    )
    required_language_ids = fields.Many2many(
        "security.language",
        "security_shift_requirement_language_rel",
        "requirement_id",
        "language_id",
        string="Required Languages",
    )
    required_attribute_ids = fields.Many2many(
        "security.attribute",
        "security_shift_requirement_attribute_rel",
        "requirement_id",
        "attribute_id",
        string="Required Attributes",
    )
    preferred_employee_id = fields.Many2one(
        "hr.employee",
        domain=[("security_guard", "=", True)],
        string="Preferred Guard",
        help="Guard to auto-assign when generating roster slots. Falls back to scoring engine if unavailable.",
    )
    allow_preferred_only = fields.Boolean(
        default=False,
        string="Preferred Guard Only",
        help="If enabled, only the preferred guard should fill this shift. Any other assignment triggers a warning.",
    )
    active = fields.Boolean(default=True)
    note = fields.Text()
    contract_active = fields.Boolean(
        compute="_compute_contract_active",
        string="Contract Active",
        help="Whether the client has an active contract covering this site today.",
    )

    @api.depends("site_id")
    def _compute_contract_active(self):
        today = fields.Date.context_today(self)
        contract_model = self.env.get("security.client.contract")
        for req in self:
            if contract_model and req.site_id and req.site_id.partner_id:
                req.contract_active = bool(
                    contract_model.get_active_for_site(req.site_id, today)
                )
            else:
                req.contract_active = True  # no contract module installed — no gate

    def _is_active_on_date(self, target_date):
        self.ensure_one()
        weekday = target_date.weekday()
        return [
            self.monday,
            self.tuesday,
            self.wednesday,
            self.thursday,
            self.friday,
            self.saturday,
            self.sunday,
        ][weekday]

    @api.depends("site_id", "post_id", "shift_template_id")
    def _compute_name(self):
        for requirement in self:
            parts = [
                requirement.site_id.name or "",
                requirement.post_id.name or "",
                requirement.shift_template_id.name or "",
            ]
            requirement.name = " - ".join(part for part in parts if part) or "Shift Requirement"

    @api.onchange("post_id")
    def _onchange_post_id(self):
        for requirement in self:
            if requirement.post_id:
                requirement.site_id = requirement.post_id.site_id

    @api.constrains("guard_count", "bill_rate", "pay_rate", "rate_multiplier", "fairness_weight")
    def _check_values(self):
        for requirement in self:
            if requirement.guard_count < 1:
                raise ValidationError("Shift requirement guard count must be at least one.")
            if requirement.bill_rate < 0 or requirement.pay_rate < 0:
                raise ValidationError("Shift requirement rates cannot be negative.")
            if requirement.rate_multiplier <= 0:
                raise ValidationError("Shift requirement rate multiplier must be greater than zero.")
            if requirement.fairness_weight < 0:
                raise ValidationError("Fairness weight cannot be negative.")


class SecuritySiteRequirement(models.Model):
    _name = "security.site.requirement"
    _description = "Security Site Requirement"
    _order = "partner_id, post_type_id"

    name = fields.Char(compute="_compute_name", store=True)
    partner_id = fields.Many2one("res.partner", required=True, string="Client", domain=[("is_company", "=", True)])
    post_type_id = fields.Many2one("security.post.type", required=True)
    minimum_guard_count = fields.Integer(default=1)
    site_id = fields.Many2one("security.client.site", string="Client Site", domain="[('partner_id','=',partner_id)]")
    minimum_reliability_score = fields.Integer(default=0)
    required_language_ids = fields.Many2many(
        "security.language",
        "security_site_requirement_language_rel",
        "requirement_id",
        "language_id",
        string="Required Languages",
    )
    required_attribute_ids = fields.Many2many(
        "security.attribute",
        "security_site_requirement_attribute_rel",
        "requirement_id",
        "attribute_id",
        string="Required Attributes",
    )
    preferred_guard_ids = fields.Many2many(
        "hr.employee",
        "security_site_requirement_employee_rel",
        "requirement_id",
        "employee_id",
        domain=[("security_guard", "=", True)],
        string="Preferred Guards",
    )
    note = fields.Text()

    @api.onchange("site_id")
    def _onchange_site_id(self):
        for req in self:
            if req.site_id and req.site_id.partner_id:
                req.partner_id = req.site_id.partner_id

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        for req in self:
            if req.site_id and req.site_id.partner_id != req.partner_id:
                req.site_id = False

    @api.depends("partner_id", "post_type_id")
    def _compute_name(self):
        for requirement in self:
            partner = requirement.partner_id.name or ""
            post_type = requirement.post_type_id.name or ""
            requirement.name = f"{partner} - {post_type}".strip(" -")


class SecurityGuardExclusion(models.Model):
    _name = "security.guard.exclusion"
    _description = "Security Guard Client/Site Exclusion"
    _order = "partner_id, site_id, employee_id"

    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        domain=[("security_guard", "=", True)],
        string="Guard",
    )
    partner_id = fields.Many2one("res.partner", string="Client", domain=[("is_company", "=", True)])
    site_id = fields.Many2one("security.client.site", string="Client Site", domain="[('partner_id','=',partner_id)]")
    reason = fields.Char(required=True)
    active = fields.Boolean(default=True)
    note = fields.Text()

    @api.onchange("site_id")
    def _onchange_site_id(self):
        for exclusion in self:
            if exclusion.site_id:
                exclusion.partner_id = exclusion.site_id.partner_id

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        for exclusion in self:
            if exclusion.site_id and exclusion.site_id.partner_id != exclusion.partner_id:
                exclusion.site_id = False

    @api.constrains("partner_id", "site_id")
    def _check_scope(self):
        for exclusion in self:
            if not exclusion.partner_id and not exclusion.site_id:
                raise ValidationError("Choose a client or client site for the exclusion.")


class SecurityRosterBatch(models.Model):
    _name = "security.roster.batch"
    _description = "Security Monthly Roster Batch"
    _order = "date_from desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    partner_id = fields.Many2one("res.partner", string="Client", domain=[("is_company", "=", True)])
    site_id = fields.Many2one("security.client.site", string="Client Site", domain="[('partner_id','=',partner_id)]")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("generated", "Generated"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("confirmed", "Confirmed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
    )
    slot_ids = fields.One2many("security.roster.slot", "batch_id", string="Roster Slots")
    generated_slot_count = fields.Integer(compute="_compute_generated_slot_count")
    planned_revenue = fields.Float(
        compute="_compute_planned_revenue",
        string="Planned Revenue",
        digits=(10, 2),
    )
    submitted_by_id = fields.Many2one("res.users", readonly=True, string="Submitted By")
    approved_by_id = fields.Many2one("res.users", readonly=True, string="Approved By")
    rejection_reason = fields.Text(string="Rejection Reason")
    note = fields.Text()

    @api.depends("date_from", "date_to", "partner_id", "site_id")
    def _compute_name(self):
        for batch in self:
            scope = batch.site_id.name or batch.partner_id.name or "All Sites"
            if batch.date_from and batch.date_to:
                batch.name = f"{scope}: {batch.date_from} to {batch.date_to}"
            else:
                batch.name = scope

    def _compute_generated_slot_count(self):
        for batch in self:
            batch.generated_slot_count = len(batch.slot_ids)

    def _compute_planned_revenue(self):
        contract_model = self.env.get("security.client.contract")
        holiday_model = self.env.get("security.public.holiday")
        for batch in self:
            if not contract_model:
                batch.planned_revenue = 0.0
                continue
            total = 0.0
            for slot in batch.slot_ids:
                if slot.state == "cancelled":
                    continue
                if not slot.shift_date or not slot.shift_template_id:
                    continue
                site = slot.site_id
                if not site:
                    continue
                contract = contract_model.get_active_for_site(site, slot.shift_date)
                if not contract:
                    continue
                # Determine primary billing category for this slot
                category = "normal"
                if holiday_model and slot.shift_date:
                    if holiday_model.search_count([
                        ("holiday_date", "=", slot.shift_date),
                        ("active", "=", True),
                    ]):
                        category = "public_holiday"
                if category == "normal":
                    weekday = slot.shift_date.weekday()
                    if weekday == 6:
                        category = "sunday"
                    elif weekday == 5:
                        category = "saturday"
                    else:
                        start = slot.shift_template_id.start_hour
                        if start >= 18 or start < 6:
                            category = "night"
                grade = slot.employee_id.security_grade_id if slot.employee_id else None
                rate = contract.get_rate_for(grade, category)
                hours = slot.shift_template_id.duration_hours or max(
                    0.0, slot.shift_template_id.end_hour - slot.shift_template_id.start_hour
                )
                if hours <= 0:
                    hours += 24.0
                total += hours * rate
            batch.planned_revenue = round(total, 2)

    @api.onchange("site_id")
    def _onchange_site_id(self):
        for batch in self:
            if batch.site_id:
                batch.partner_id = batch.site_id.partner_id

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        for batch in self:
            if batch.site_id and batch.site_id.partner_id != batch.partner_id:
                batch.site_id = False

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for batch in self:
            if batch.date_to < batch.date_from:
                raise ValidationError("Roster batch end date cannot be earlier than start date.")

    def action_generate_slots(self):
        slot_model = self.env["security.roster.slot"]
        requirement_model = self.env["security.shift.requirement"]
        for batch in self:
            domain = [("active", "=", True)]
            if batch.site_id:
                domain.append(("site_id", "=", batch.site_id.id))
            elif batch.partner_id:
                domain.append(("partner_id", "=", batch.partner_id.id))
            requirements = requirement_model.search(domain)
            if not requirements:
                raise ValidationError("No active shift requirements found for this roster batch.")

            created_count = 0
            target_date = batch.date_from
            while target_date <= batch.date_to:
                for requirement in requirements:
                    if not requirement._is_active_on_date(target_date):
                        continue
                    for guard_number in range(requirement.guard_count):
                        existing = slot_model.search_count(
                            [
                                ("shift_date", "=", target_date),
                                ("shift_requirement_id", "=", requirement.id),
                                ("batch_id", "=", batch.id),
                                ("slot_number", "=", guard_number + 1),
                            ]
                        )
                        if existing:
                            continue
                        vals = {
                            "batch_id": batch.id,
                            "slot_number": guard_number + 1,
                            "shift_date": target_date,
                            "shift_requirement_id": requirement.id,
                            "post_id": requirement.post_id.id,
                            "shift_template_id": requirement.shift_template_id.id,
                        }
                        # Pre-fill preferred guard on slot 1 only (first guard position)
                        if guard_number == 0 and requirement.preferred_employee_id:
                            preferred = requirement.preferred_employee_id
                            if not preferred.security_disqualified:
                                vals["employee_id"] = preferred.id
                                vals["state"] = "assigned"
                        slot_model.create(vals)
                        created_count += 1
                target_date += timedelta(days=1)
            batch.state = "generated"
            if not created_count:
                raise ValidationError("No new roster slots were created. Check dates or existing slots.")

    def action_confirm(self):
        contract_model = self.env.get("security.client.contract")
        for batch in self:
            if contract_model:
                # Validate every site in this batch has an active contract on date_from.
                # Mid-month expiry is caught here — ops managers see the problem via the
                # contract_active badge on ShiftRequirement before generating a new batch.
                sites = batch.slot_ids.mapped("site_id")
                for site in sites:
                    if not site.partner_id:
                        continue
                    contract = contract_model.get_active_for_site(site, batch.date_from)
                    if not contract:
                        raise ValidationError(
                            f"No active contract for site '{site.name}' "
                            f"(client: {site.partner_id.name}). "
                            "Activate a client contract before confirming this roster."
                        )
            batch.slot_ids.write({"state": "confirmed"})
            batch.state = "confirmed"
            if "security.notification" in self.env:
                sites = batch.slot_ids.mapped("site_id")
                supervisor_users = self.env["res.users"].browse()
                for site in sites:
                    if site.supervisor_id and site.supervisor_id.user_id:
                        supervisor_users |= site.supervisor_id.user_id
                if supervisor_users:
                    self.env["security.notification"].sudo().create({
                        "title": f"Roster Confirmed: {batch.name}",
                        "body": (
                            f"Roster '{batch.name}' has been confirmed. "
                            "Your shift assignments are now locked in."
                        ),
                        "notification_type": "roster_gap",
                        "severity": "info",
                        "recipient_ids": [(6, 0, supervisor_users.ids)],
                        "related_model": "security.roster.batch",
                        "related_id": batch.id,
                    })

    def action_cancel(self):
        for batch in self:
            batch.state = "cancelled"

    def action_reset_to_draft(self):
        for batch in self:
            batch.state = "draft"

    def action_submit(self):
        for batch in self:
            batch.state = "submitted"
            batch.submitted_by_id = self.env.user.id
            if "security.notification" in self.env:
                self.env["security.notification"].sudo().create({
                    "title": f"Roster Submitted: {batch.name}",
                    "body": (
                        f"Roster batch '{batch.name}' has been submitted for approval"
                        f" by {self.env.user.name}."
                    ),
                    "notification_type": "roster_gap",
                    "severity": "info",
                })

    def action_approve(self):
        for batch in self:
            batch.state = "approved"
            batch.approved_by_id = self.env.user.id

    def action_reject(self):
        for batch in self:
            batch.state = "draft"

    def action_copy_from_previous_month(self):
        """Copy all confirmed slots from the most recent previous batch."""
        self.ensure_one()
        prev_batch = self.search(
            [("id", "!=", self.id), ("date_from", "<", self.date_from)],
            order="date_from desc",
            limit=1,
        )
        if not prev_batch:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "No Previous Roster",
                    "message": "No previous roster batch found.",
                    "type": "warning",
                },
            }
        month_diff = (
            (self.date_from.year - prev_batch.date_from.year) * 12
            + (self.date_from.month - prev_batch.date_from.month)
        )
        created = 0
        for slot in prev_batch.slot_ids.filtered(lambda s: s.state == "confirmed"):
            new_date = slot.shift_date + relativedelta(months=month_diff)
            if self.date_from <= new_date <= self.date_to:
                if not slot.post_id or not slot.shift_template_id:
                    continue
                slot_vals = {
                    "batch_id": self.id,
                    "post_id": slot.post_id.id,
                    "shift_date": new_date,
                    "shift_template_id": slot.shift_template_id.id,
                    "shift_requirement_id": slot.shift_requirement_id.id if slot.shift_requirement_id else False,
                    "state": "draft",
                }
                if slot.employee_id:
                    slot_vals["employee_id"] = slot.employee_id.id
                self.env["security.roster.slot"].create(slot_vals)
                created += 1
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Roster Copied",
                "message": f"{created} slots copied from {prev_batch.name}.",
                "type": "success",
            },
        }

    def action_auto_fill_open_slots(self):
        """Assign the top scoring eligible guard to every unassigned slot in this batch."""
        for batch in self:
            open_slots = batch.slot_ids.filtered(lambda s: not s.employee_id and s.state != "cancelled")
            filled = 0
            for slot in open_slots:
                req = slot.shift_requirement_id
                domain = [("security_guard", "=", True), ("active", "=", True), ("security_disqualified", "=", False)]
                candidates = self.env["hr.employee"].search(domain)
                # Filter: no double-booking on same date
                already_assigned = self.env["security.roster.slot"].search([
                    ("shift_date", "=", slot.shift_date),
                    ("employee_id", "in", candidates.ids),
                    ("id", "!=", slot.id),
                    ("state", "!=", "cancelled"),
                ]).mapped("employee_id").ids
                candidates = candidates.filtered(lambda e: e.id not in already_assigned)
                # Filter: grade requirement
                if req and slot.post_type_id and slot.post_type_id.min_grade_id:
                    min_seq = slot.post_type_id.min_grade_id.sequence
                    candidates = candidates.filtered(
                        lambda e: e.security_grade_id and e.security_grade_id.sequence <= min_seq
                    )
                # Filter: site exclusions
                excluded = self.env["security.guard.exclusion"].search([
                    ("active", "=", True),
                    "|",
                    ("site_id", "=", slot.site_id.id or False),
                    ("partner_id", "=", slot.partner_id.id or False),
                ]).mapped("employee_id").ids
                candidates = candidates.filtered(lambda e: e.id not in excluded)
                if not candidates:
                    continue
                # Prefer preferred guard if set and eligible
                chosen = None
                if req and req.preferred_employee_id and req.preferred_employee_id in candidates:
                    chosen = req.preferred_employee_id
                else:
                    # Pick by reliability score desc
                    scored = candidates.sorted(
                        key=lambda e: e.security_reliability_score if hasattr(e, "security_reliability_score") else 0,
                        reverse=True,
                    )
                    chosen = scored[0] if scored else None
                if chosen:
                    slot.write({"employee_id": chosen.id, "state": "assigned"})
                    filled += 1
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Auto-Fill Complete",
                    "message": f"{filled} of {len(open_slots)} open slots filled.",
                    "type": "success" if filled == len(open_slots) else "warning",
                },
            }

    def action_auto_fill_slots(self):
        """Auto-assign available guards to all empty (unassigned) slots in this batch."""
        self.ensure_one()
        empty_slots = self.slot_ids.filtered(lambda s: not s.employee_id and s.state == "draft")
        if not empty_slots:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "No Gaps Found",
                    "message": "All slots in this batch already have guards assigned.",
                    "type": "info",
                },
            }
        guards = self.env["hr.employee"].search([("security_guard", "=", True), ("active", "=", True)])
        if not guards:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "No Guards Available",
                    "message": "No active security guards found in the system.",
                    "type": "warning",
                },
            }
        assigned = 0
        skipped = 0
        for slot in empty_slots:
            busy_guard_ids = set(
                self.env["security.roster.slot"].search([
                    ("shift_date", "=", slot.shift_date),
                    ("employee_id", "!=", False),
                    ("state", "not in", ["cancelled"]),
                    ("id", "!=", slot.id),
                ]).mapped("employee_id").ids
            )
            available = guards.filtered(lambda g: g.id not in busy_guard_ids)
            if not available:
                skipped += 1
                continue
            slot.write({"employee_id": available[0].id, "state": "assigned"})
            assigned += 1
        msg = f"{assigned} slot(s) filled."
        if skipped:
            msg += f" {skipped} slot(s) could not be filled (no available guard)."
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Auto-Fill Complete",
                "message": msg,
                "type": "success" if assigned else "warning",
            },
        }

    @api.model
    def action_cron_auto_generate_next_month_batches(self):
        """Cron (runs on the 20th): auto-create next month's roster batch for every active billing plan."""
        today = date.today()
        next_month = today + relativedelta(months=1)
        first_day = next_month.replace(day=1)
        last_day = next_month.replace(day=calendar.monthrange(next_month.year, next_month.month)[1])

        billing_model = self.env.get("security.billing.plan")
        if not billing_model:
            return

        active_plans = billing_model.search([("active", "=", True)])
        req_model = self.env["security.shift.requirement"]
        notif_model = self.env.get("security.notification")

        created_batches = 0
        total_slots = 0

        for plan in active_plans:
            # Find all active sites linked to this client via shift requirements
            requirements = req_model.search([
                ("partner_id", "=", plan.partner_id.id),
                ("active", "=", True),
            ])
            sites = requirements.mapped("site_id")

            for site in sites:
                # Skip if a batch already exists for this site + month
                existing = self.search([
                    ("site_id", "=", site.id),
                    ("date_from", "=", str(first_day)),
                    ("date_to", "=", str(last_day)),
                ], limit=1)
                if existing:
                    continue

                batch = self.create({
                    "date_from": first_day,
                    "date_to": last_day,
                    "site_id": site.id,
                    "partner_id": plan.partner_id.id,
                })
                try:
                    batch.action_generate_slots()
                    total_slots += batch.generated_slot_count
                    created_batches += 1
                except ValidationError:
                    batch.unlink()
                    continue

        if notif_model and created_batches:
            notif_model.sudo().create({
                "title": f"Roster Auto-Generated: {first_day.strftime('%B %Y')}",
                "body": (
                    f"{created_batches} roster batch(es) auto-created for "
                    f"{first_day.strftime('%B %Y')} with {total_slots} slots. "
                    "Please assign guards before the month starts."
                ),
                "notification_type": "roster_gap",
                "severity": "info",
            })

    def action_generate_next_month(self):
        """Manual trigger: generate next month's roster for this batch's site/client."""
        today = date.today()
        next_month = today + relativedelta(months=1)
        first_day = next_month.replace(day=1)
        last_day = next_month.replace(day=calendar.monthrange(next_month.year, next_month.month)[1])

        for batch in self:
            existing = self.search([
                ("site_id", "=", batch.site_id.id),
                ("partner_id", "=", batch.partner_id.id),
                ("date_from", "=", str(first_day)),
            ], limit=1)
            if existing:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Already Exists",
                        "message": f"A roster batch for {first_day.strftime('%B %Y')} already exists for this site.",
                        "type": "warning",
                    },
                }
            new_batch = self.create({
                "date_from": first_day,
                "date_to": last_day,
                "site_id": batch.site_id.id,
                "partner_id": batch.partner_id.id,
            })
            new_batch.action_generate_slots()
            return {
                "type": "ir.actions.act_window",
                "res_model": "security.roster.batch",
                "res_id": new_batch.id,
                "views": [[False, "form"]],
                "target": "current",
            }


class SecurityRosterSlot(models.Model):
    _name = "security.roster.slot"
    _description = "Security Roster Slot"
    _order = "shift_date, shift_template_id, post_id"

    name = fields.Char(compute="_compute_name", store=True)
    batch_id = fields.Many2one("security.roster.batch", ondelete="set null")
    slot_number = fields.Integer(default=1)
    shift_date = fields.Date(required=True)
    shift_requirement_id = fields.Many2one("security.shift.requirement")
    post_id = fields.Many2one("security.post", required=True)
    partner_id = fields.Many2one(related="post_id.partner_id", store=True)
    site_id = fields.Many2one(related="post_id.site_id", store=True)
    post_type_id = fields.Many2one(related="post_id.post_type_id", store=True)
    shift_template_id = fields.Many2one(
        "security.shift.template",
        required=True,
    )
    employee_id = fields.Many2one(
        "hr.employee",
        domain=[("security_guard", "=", True)],
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("assigned", "Assigned"),
            ("confirmed", "Confirmed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
    )
    override_reason = fields.Char()
    overtime_planned = fields.Boolean(default=False)
    high_value_shift = fields.Boolean(
        compute="_compute_shift_flags",
        store=True,
    )
    fairness_warning = fields.Char(
        compute="_compute_fairness_warning",
        store=True,
    )
    note = fields.Text()

    @api.onchange("shift_requirement_id")
    def _onchange_shift_requirement_id(self):
        for slot in self:
            if slot.shift_requirement_id:
                slot.post_id = slot.shift_requirement_id.post_id
                slot.shift_template_id = slot.shift_requirement_id.shift_template_id

    @api.depends("shift_requirement_id.rate_multiplier", "shift_requirement_id.fairness_weight")
    def _compute_shift_flags(self):
        for slot in self:
            requirement = slot.shift_requirement_id
            slot.high_value_shift = bool(
                requirement
                and (requirement.rate_multiplier > 1.0 or requirement.fairness_weight > 1.0)
            )

    @api.depends("employee_id", "shift_date", "high_value_shift", "batch_id")
    def _compute_fairness_warning(self):
        for slot in self:
            slot.fairness_warning = False
            if not slot.employee_id or not slot.high_value_shift or not slot.shift_date:
                continue
            date_from = slot.batch_id.date_from if slot.batch_id else slot.shift_date.replace(day=1)
            date_to = slot.batch_id.date_to if slot.batch_id else slot.shift_date
            high_value_count = self.search_count(
                [
                    ("employee_id", "=", slot.employee_id.id),
                    ("high_value_shift", "=", True),
                    ("shift_date", ">=", date_from),
                    ("shift_date", "<=", date_to),
                    ("id", "!=", slot.id),
                ]
            )
            if high_value_count >= 5:
                slot.fairness_warning = "Guard already has several high-value shifts in this period."

    @api.depends("shift_date", "post_id", "employee_id")
    def _compute_name(self):
        for slot in self:
            date = slot.shift_date or ""
            post = slot.post_id.name or ""
            employee = slot.employee_id.name or "Unassigned"
            slot.name = f"{date} - {post} - {employee}"

    @api.constrains("employee_id", "post_id", "shift_requirement_id")
    def _check_guard_eligibility(self):
        for slot in self:
            employee = slot.employee_id
            post_type = slot.post_id.post_type_id
            requirement = slot.shift_requirement_id
            if not employee or not post_type:
                continue
            if employee.security_disqualified:
                raise ValidationError(
                    "Disqualified guards cannot be assigned to roster slots."
                )
            if slot.site_id or slot.partner_id:
                exclusion_domain = [
                    ("employee_id", "=", employee.id),
                    ("active", "=", True),
                    "|",
                    ("site_id", "=", slot.site_id.id or False),
                    ("partner_id", "=", slot.partner_id.id or False),
                ]
                if self.env["security.guard.exclusion"].search_count(exclusion_domain):
                    raise ValidationError(
                        "This guard is excluded from this client or site."
                    )
            if post_type.min_grade_id and employee.security_grade_id:
                if employee.security_grade_id.sequence < post_type.min_grade_id.sequence:
                    raise ValidationError(
                        "The assigned guard does not meet the minimum grade for this post type."
                    )
            elif post_type.min_grade_id and not employee.security_grade_id:
                raise ValidationError(
                    "The assigned guard has no grade but this post requires one."
                )

            missing_certifications = (
                post_type.required_certification_ids - employee.security_certification_ids
            )
            if requirement:
                missing_certifications |= (
                    requirement.required_certification_ids - employee.security_certification_ids
                )
            if missing_certifications:
                raise ValidationError(
                    "The assigned guard is missing required certifications for this post type."
                )

            # Check that no required certification has an expired linked document.
            if hasattr(employee, "get_expired_certification_ids"):
                expired_cert_ids = employee.get_expired_certification_ids()
                if expired_cert_ids:
                    required_cert_ids = set(post_type.required_certification_ids.ids)
                    if requirement:
                        required_cert_ids |= set(requirement.required_certification_ids.ids)
                    expired_required = required_cert_ids & expired_cert_ids
                    if expired_required:
                        cert_names = self.env["security.certification"].browse(
                            list(expired_required)
                        ).mapped("name")
                        raise ValidationError(
                            "The following required certifications have expired: %s"
                            % ", ".join(cert_names)
                        )
            if post_type.required_language_ids - employee.security_language_ids:
                raise ValidationError(
                    "The assigned guard is missing required languages for this post type."
                )
            if post_type.required_attribute_ids - employee.security_attribute_ids:
                raise ValidationError(
                    "The assigned guard is missing required attributes for this post type."
                )
            if requirement:
                if requirement.required_language_ids - employee.security_language_ids:
                    raise ValidationError(
                        "The assigned guard is missing required languages for this shift requirement."
                    )
                if requirement.required_attribute_ids - employee.security_attribute_ids:
                    raise ValidationError(
                        "The assigned guard is missing required attributes for this shift requirement."
                    )
                minimum_score = max(
                    post_type.minimum_reliability_score,
                    requirement.minimum_reliability_score,
                )
            else:
                minimum_score = post_type.minimum_reliability_score
            if employee.security_reliability_score < minimum_score:
                raise ValidationError(
                    "The assigned guard does not meet the minimum reliability score."
                )

    @api.model
    def action_batch_assign(self, slot_ids, employee_id):
        """Assign employee_id to all slot_ids, skipping slots that fail eligibility."""
        slots = self.browse(slot_ids)
        employee = self.env["hr.employee"].browse(employee_id)
        assigned = []
        skipped = []
        for slot in slots:
            if slot.employee_id:
                skipped.append(f"{slot.name} (already assigned)")
                continue
            try:
                slot.write({"employee_id": employee.id, "state": "assigned"})
                assigned.append(slot.name)
            except ValidationError as e:
                skipped.append(f"{slot.name} ({e.args[0]})")
        msg_parts = [f"{len(assigned)} slot(s) assigned to {employee.name}."]
        if skipped:
            msg_parts.append(
                f"{len(skipped)} skipped: {'; '.join(skipped[:3])}"
                f"{'…' if len(skipped) > 3 else ''}"
            )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Batch Assign Complete",
                "message": " ".join(msg_parts),
                "type": "success" if not skipped else "warning",
            },
        }
