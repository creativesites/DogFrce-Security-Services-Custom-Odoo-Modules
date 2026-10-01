from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SecurityContractShiftRequirement(models.Model):
    _name = "security.contract.shift.requirement"
    _description = "Contract Shift Requirement Recipe"
    _order = "sequence, id"

    contract_id = fields.Many2one(
        "security.client.contract",
        related="contract_site_id.contract_id",
        store=True,
        index=True,
        string="Contract",
    )
    contract_site_id = fields.Many2one(
        "security.contract.site",
        required=True,
        ondelete="cascade",
        index=True,
        string="Contract Site",
    )
    contract_post_id = fields.Many2one(
        "security.contract.post",
        required=True,
        ondelete="cascade",
        index=True,
        string="Post",
    )
    sequence = fields.Integer(default=10)
    shift_template_id = fields.Many2one(
        "security.shift.template",
        required=True,
        string="Shift Template",
    )

    # Days of week
    monday = fields.Boolean(default=True, string="Mon")
    tuesday = fields.Boolean(default=True, string="Tue")
    wednesday = fields.Boolean(default=True, string="Wed")
    thursday = fields.Boolean(default=True, string="Thu")
    friday = fields.Boolean(default=True, string="Fri")
    saturday = fields.Boolean(default=True, string="Sat")
    sunday = fields.Boolean(default=True, string="Sun")

    guard_count = fields.Integer(
        default=1,
        required=True,
        string="Guard Count",
        help="Number of guards assigned concurrently on this shift.",
    )
    min_grade_id = fields.Many2one(
        "security.grade",
        string="Minimum Grade",
        help="Minimum security grade required for this shift.",
    )
    required_certification_ids = fields.Many2many(
        "security.certification",
        "sec_contract_req_cert_rel",
        "req_id",
        "cert_id",
        string="Required Certifications",
    )
    required_language_ids = fields.Many2many(
        "security.language",
        "sec_contract_req_lang_rel",
        "req_id",
        "lang_id",
        string="Required Languages",
    )
    required_attribute_ids = fields.Many2many(
        "security.attribute",
        "sec_contract_req_attr_rel",
        "req_id",
        "attr_id",
        string="Required Attributes",
    )
    preferred_employee_id = fields.Many2one(
        "hr.employee",
        string="Preferred Guard",
        domain=[("security_guard", "=", True)],
    )
    allow_preferred_only = fields.Boolean(
        string="Preferred Guard Only",
        default=False,
    )

    # Pricing & Overrides
    contract_bill_rate = fields.Float(
        compute="_compute_contract_rates",
        string="Contract Base Rate",
        digits=(10, 2),
    )
    bill_rate = fields.Float(
        string="Billing Rate (N$/hr)",
        compute="_compute_rates",
        store=True,
        readonly=False,
        digits=(10, 2),
    )
    bill_rate_override = fields.Boolean(
        string="Override Bill Rate",
        default=False,
    )

    contract_pay_rate = fields.Float(
        compute="_compute_contract_rates",
        string="Standard Pay Rate",
        digits=(10, 2),
    )
    pay_rate = fields.Float(
        string="Pay Rate (N$/hr)",
        compute="_compute_rates",
        store=True,
        readonly=False,
        digits=(10, 2),
    )
    pay_rate_override = fields.Boolean(
        string="Override Pay Rate",
        default=False,
    )
    override_reason = fields.Char(string="Rate Override Reason")

    rate_multiplier = fields.Float(default=1.0, string="Rate Multiplier")
    fairness_weight = fields.Float(default=1.0, string="Fairness Weight")

    # Extra / Surge Cover
    is_extra_cover = fields.Boolean(
        default=False,
        string="Temporary / Extra Cover",
    )
    date_start = fields.Date(string="Extra Cover Start")
    date_end = fields.Date(string="Extra Cover End")

    requirement_id = fields.Many2one(
        "security.shift.requirement",
        string="Linked Operational Requirement",
        ondelete="set null",
    )

    days_active_count = fields.Integer(
        compute="_compute_days_active",
        store=True,
        string="Active Days / Week",
    )
    estimated_monthly_slots = fields.Integer(
        compute="_compute_estimated_monthly_slots",
        store=True,
        string="Est. Monthly Slots",
    )

    @api.onchange("contract_post_id")
    def _onchange_contract_post_id(self):
        if self.contract_post_id and self.contract_post_id.min_grade_id and not self.min_grade_id:
            self.min_grade_id = self.contract_post_id.min_grade_id

    @api.depends("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
    def _compute_days_active(self):
        for req in self:
            req.days_active_count = sum([
                bool(req.monday),
                bool(req.tuesday),
                bool(req.wednesday),
                bool(req.thursday),
                bool(req.friday),
                bool(req.saturday),
                bool(req.sunday),
            ])

    @api.depends("days_active_count", "guard_count")
    def _compute_estimated_monthly_slots(self):
        for req in self:
            # 30.4 days avg in a monthly operational cycle
            weeks_in_cycle = 30.4 / 7.0
            req.estimated_monthly_slots = int(round(req.days_active_count * (req.guard_count or 1) * weeks_in_cycle))

    def _get_shift_category(self):
        """Determine shift category based on template start time."""
        if not self.shift_template_id:
            return "normal"
        start = self.shift_template_id.start_hour
        if start >= 18 or start < 6:
            return "night"
        return "normal"

    @api.depends("contract_id.rate_line_ids", "min_grade_id", "shift_template_id")
    def _compute_contract_rates(self):
        for req in self:
            cat = req._get_shift_category()
            c_bill = 0.0
            c_pay = 0.0
            if req.contract_id:
                c_bill = req.contract_id.get_rate_for(req.min_grade_id, cat)
            if req.min_grade_id and hasattr(req.min_grade_id, "hourly_rate"):
                c_pay = req.min_grade_id.hourly_rate or 0.0
            elif req.contract_id:
                # Default baseline pay is usually 70-80% of bill rate if not set on grade
                c_pay = round(c_bill * 0.75, 2)
            req.contract_bill_rate = c_bill
            req.contract_pay_rate = c_pay

    @api.depends("contract_bill_rate", "contract_pay_rate", "bill_rate_override", "pay_rate_override")
    def _compute_rates(self):
        for req in self:
            if not req.bill_rate_override or not req.bill_rate:
                req.bill_rate = req.contract_bill_rate
            if not req.pay_rate_override or not req.pay_rate:
                req.pay_rate = req.contract_pay_rate

    def action_duplicate_shift(self):
        """Quick duplicate of this shift requirement."""
        self.ensure_one()
        new_req = self.copy({
            "requirement_id": False,
        })
        return True

    def action_copy_to_all_days(self):
        """Apply active status to all Mon-Sun days."""
        self.write({
            "monday": True,
            "tuesday": True,
            "wednesday": True,
            "thursday": True,
            "friday": True,
            "saturday": True,
            "sunday": True,
        })
        return True
