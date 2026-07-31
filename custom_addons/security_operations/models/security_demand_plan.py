import math
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SecurityDemandPlan(models.Model):
    _name = "security.demand.plan"
    _description = "Security Demand & Contract Sizing Estimator"
    _order = "create_date desc"

    name = fields.Char(
        string="Plan Title / Reference",
        required=True,
        default="New Contract Sizing Plan",
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Client",
        domain="[('is_company', '=', True)]",
        help="Target or existing client for this contract estimate.",
    )
    site_name = fields.Char(
        string="Proposed Site Name",
        default="Main Facility / Mine Expansion",
    )
    site_type = fields.Selection(
        [
            ("mining", "Mining / Heavy Industrial"),
            ("industrial", "Factory / Warehouse"),
            ("commercial", "Commercial / Office Complex"),
            ("residential", "Residential Estate"),
            ("retail", "Retail / Shopping Mall"),
            ("embassy", "Embassy / High Security"),
            ("banking", "Banking / Financial"),
        ],
        string="Site Sector",
        default="mining",
        required=True,
    )
    start_date = fields.Date(
        string="Contract Start Date",
        default=fields.Date.context_today,
        required=True,
    )

    # Operational Requirements (User Inputs)
    posts_count = fields.Integer(
        string="On-Duty Guard Posts Count",
        default=24,
        required=True,
        help="Number of guards needed on post simultaneously at any given hour.",
    )
    shift_duration = fields.Selection(
        [
            ("12h", "12-Hour Shifts"),
            ("8h", "8-Hour Shifts"),
        ],
        string="Shift Duration",
        default="12h",
        required=True,
    )
    operating_schedule = fields.Selection(
        [
            ("24_7", "24/7 Continuous (168 hrs/wk)"),
            ("day_12", "Day Shifts Only - 12h x 7 Days (84 hrs/wk)"),
            ("night_12", "Night Shifts Only - 12h x 7 Days (84 hrs/wk)"),
            ("business_8", "Standard Business - 8h x 5 Days (40 hrs/wk)"),
        ],
        string="Operating Schedule",
        default="24_7",
        required=True,
    )
    rotation_pattern = fields.Selection(
        [
            ("4_2", "4 Days On / 2 Days Off (Rest Rotation)"),
            ("6_1", "6 Days On / 1 Day Off"),
            ("2_2_2", "2 Day / 2 Night / 2 Off (Standard 12h Rotation)"),
        ],
        string="Guard Shift Rotation",
        default="2_2_2",
        required=True,
    )
    relief_factor = fields.Float(
        string="Relief Coverage Multiplier",
        default=1.333,
        digits=(5, 3),
        help="Coverage multiplier factoring rest days, leave, and sick reserve. Default 1.33x for 24/7 12h shifts.",
    )

    # Executive Output Sizing & Asset Allocations (Computed)
    needed_guards = fields.Integer(
        string="Guards Needed (Headcount)",
        compute="_compute_sizing_and_finances",
        store=True,
    )
    needed_supervisors = fields.Integer(
        string="Supervisors Needed",
        compute="_compute_sizing_and_finances",
        store=True,
    )
    needed_vehicles = fields.Integer(
        string="Patrol Vehicles Needed",
        compute="_compute_sizing_and_finances",
        store=True,
    )
    needed_radios = fields.Integer(
        string="Two-Way Radios Needed",
        compute="_compute_sizing_and_finances",
        store=True,
    )
    needed_torches = fields.Integer(
        string="Heavy Duty Torches Needed",
        compute="_compute_sizing_and_finances",
        store=True,
    )
    needed_bodycams = fields.Integer(
        string="Body Cams Needed",
        compute="_compute_sizing_and_finances",
        store=True,
    )
    needed_uniform_kits = fields.Integer(
        string="Uniform Kits Needed",
        compute="_compute_sizing_and_finances",
        store=True,
    )

    # Financial Rates & Cost Projections
    guard_monthly_pay = fields.Float(
        string="Guard Monthly Pay Rate (ZMW)",
        default=4500.0,
        required=True,
    )
    supervisor_monthly_pay = fields.Float(
        string="Supervisor Monthly Pay Rate (ZMW)",
        default=6500.0,
        required=True,
    )
    vehicle_monthly_cost = fields.Float(
        string="Vehicle Monthly Operating Cost (ZMW)",
        default=12000.0,
        help="Fuel, maintenance, insurance, and wear per vehicle.",
    )
    bill_rate_per_post_hour = fields.Float(
        string="Post Bill Rate / Hour (ZMW)",
        default=38.50,
        required=True,
        help="Client bill rate per post hour.",
    )

    # Computed Financial Results
    total_monthly_post_hours = fields.Float(
        string="Total Monthly Post Hours",
        compute="_compute_sizing_and_finances",
        store=True,
    )
    monthly_bill_revenue = fields.Float(
        string="Monthly Bill Revenue (ZMW)",
        compute="_compute_sizing_and_finances",
        store=True,
    )
    monthly_guard_payroll = fields.Float(
        string="Guard Payroll Cost (ZMW)",
        compute="_compute_sizing_and_finances",
        store=True,
    )
    monthly_supervisor_payroll = fields.Float(
        string="Supervisor Payroll Cost (ZMW)",
        compute="_compute_sizing_and_finances",
        store=True,
    )
    monthly_payroll_cost = fields.Float(
        string="Total Payroll Cost (ZMW)",
        compute="_compute_sizing_and_finances",
        store=True,
    )
    monthly_equipment_cost = fields.Float(
        string="Monthly Equipment Operating Cost (ZMW)",
        compute="_compute_sizing_and_finances",
        store=True,
    )
    monthly_gross_profit = fields.Float(
        string="Projected Monthly Gross Profit (ZMW)",
        compute="_compute_sizing_and_finances",
        store=True,
    )
    gross_margin_pct = fields.Float(
        string="Gross Margin (%)",
        compute="_compute_sizing_and_finances",
        store=True,
        digits=(5, 1),
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("estimated", "Calculated / Estimated"),
            ("approved", "Executive Approved"),
            ("converted", "Converted to Contract"),
        ],
        default="draft",
        string="Status",
        required=True,
    )

    # Linked Contract
    converted_contract_id = fields.Many2one(
        "security.client.contract",
        string="Linked Active Contract",
        readonly=True,
    )
    converted_site_id = fields.Many2one(
        "security.client.site",
        string="Linked Active Site",
        readonly=True,
    )

    @api.onchange("rotation_pattern")
    def _onchange_rotation_pattern(self):
        for plan in self:
            if plan.rotation_pattern in ["4_2", "2_2_2"]:
                plan.relief_factor = 1.65  # 1.50 base + 10% leave/sick reserve
            elif plan.rotation_pattern == "6_1":
                plan.relief_factor = 1.28  # 1.167 base + 10% leave/sick reserve

    @api.depends(
        "posts_count",
        "shift_duration",
        "operating_schedule",
        "rotation_pattern",
        "relief_factor",
        "site_type",
        "guard_monthly_pay",
        "supervisor_monthly_pay",
        "vehicle_monthly_cost",
        "bill_rate_per_post_hour",
    )
    def _compute_sizing_and_finances(self):
        for plan in self:
            posts = max(1, plan.posts_count)

            # 1. Weekly Post Hours & Daily Shifts
            if plan.operating_schedule == "24_7":
                hours_per_week = 168.0  # 24 * 7
                shifts_per_day = 3.0 if plan.shift_duration == "8h" else 2.0
            elif plan.operating_schedule in ["day_12", "night_12"]:
                hours_per_week = 84.0   # 12 * 7
                shifts_per_day = 1.0
            else:  # business_8
                hours_per_week = 40.0   # 8 * 5
                shifts_per_day = 1.0

            # 2. Guard Headcount Sizing
            rf = plan.relief_factor if plan.relief_factor >= 1.0 else 1.333
            needed_guards = math.ceil(posts * shifts_per_day * rf)
            # Ensure minimum guards cover daily posts
            needed_guards = max(needed_guards, math.ceil(posts * shifts_per_day * 1.10))

            # 3. Supervisor Headcount
            # Standard ratio: 1 supervisor per 12 on-duty guards per shift
            guards_per_shift = posts
            supervisors_per_shift = max(1, math.ceil(guards_per_shift / 12.0))
            if plan.operating_schedule == "24_7":
                needed_supervisors = math.ceil(supervisors_per_shift * shifts_per_day * 1.25)
            else:
                needed_supervisors = supervisors_per_shift

            # 4. Equipment Sizing Rules
            # Vehicles: 1 vehicle per site for mining/industrial or large sites (> 15 posts)
            if plan.site_type in ["mining", "industrial"] or posts >= 15:
                needed_vehicles = math.ceil(posts / 20.0)
            elif plan.site_type in ["commercial", "residential"] and posts >= 8:
                needed_vehicles = 1
            else:
                needed_vehicles = 0

            # Radios: 1 per supervisor + 1 per key post (half of total posts or 1 per post if mining)
            if plan.site_type in ["mining", "embassy"]:
                needed_radios = posts + needed_supervisors
            else:
                needed_radios = math.ceil(posts / 2.0) + needed_supervisors

            # Torches: 1 per night-shift post + 1 per supervisor
            if plan.operating_schedule in ["24_7", "night_12"]:
                needed_torches = posts + needed_supervisors
            else:
                needed_torches = needed_supervisors

            # Body Cams: 1 per supervisor + high-risk posts
            if plan.site_type in ["mining", "embassy", "banking"]:
                needed_bodycams = math.ceil(posts / 3.0) + needed_supervisors
            else:
                needed_bodycams = needed_supervisors

            # Uniform Kits: 1 kit per total headcount + 10% reserve
            total_headcount = needed_guards + needed_supervisors
            needed_uniform_kits = math.ceil(total_headcount * 1.10)

            # Assign computed sizing
            plan.needed_guards = needed_guards
            plan.needed_supervisors = needed_supervisors
            plan.needed_vehicles = needed_vehicles
            plan.needed_radios = needed_radios
            plan.needed_torches = needed_torches
            plan.needed_bodycams = needed_bodycams
            plan.needed_uniform_kits = needed_uniform_kits

            # 5. Financial Calculations (Monthly average = 4.33 weeks/month)
            monthly_post_hours = round(posts * hours_per_week * 4.333, 2)
            monthly_revenue = round(monthly_post_hours * plan.bill_rate_per_post_hour, 2)

            guard_payroll = round(needed_guards * plan.guard_monthly_pay, 2)
            supervisor_payroll = round(needed_supervisors * plan.supervisor_monthly_pay, 2)
            total_payroll = guard_payroll + supervisor_payroll

            equipment_cost = round(
                (needed_vehicles * plan.vehicle_monthly_cost) +
                (needed_radios * 150.0) +
                (needed_torches * 80.0) +
                (needed_bodycams * 100.0),
                2
            )
            gross_profit = round(monthly_revenue - total_payroll - equipment_cost, 2)
            margin_pct = round((gross_profit / monthly_revenue * 100.0), 1) if monthly_revenue > 0 else 0.0

            plan.total_monthly_post_hours = monthly_post_hours
            plan.monthly_bill_revenue = monthly_revenue
            plan.monthly_guard_payroll = guard_payroll
            plan.monthly_supervisor_payroll = supervisor_payroll
            plan.monthly_payroll_cost = total_payroll
            plan.monthly_equipment_cost = equipment_cost
            plan.monthly_gross_profit = gross_profit
            plan.gross_margin_pct = margin_pct

    def action_calculate(self):
        """Trigger recalculation and transition to estimated state."""
        self.ensure_one()
        self._compute_sizing_and_finances()
        self.state = "estimated"
        return True

    def action_approve(self):
        """Approve executive demand plan."""
        self.ensure_one()
        self.state = "approved"
        return True

    def action_convert_to_contract(self):
        """
        Convert approved demand plan into a live Client Contract, Site, and Post requirement records!
        """
        self.ensure_one()
        if not self.partner_id:
            raise ValidationError(_("Please select a Client before converting to a contract."))

        # 1. Create or find Client Site
        site = self.env["security.client.site"].search([
            ("partner_id", "=", self.partner_id.id),
            ("name", "=", self.site_name),
        ], limit=1)
        if not site:
            site = self.env["security.client.site"].create({
                "name": self.site_name,
                "partner_id": self.partner_id.id,
                "active": True,
            })

        # 2. Create Client Contract
        contract = self.env["security.client.contract"].create({
            "name": f"CON-{self.partner_id.name[:3].upper()}-{self.start_date.strftime('%Y%m')}",
            "partner_id": self.partner_id.id,
            "site_id": site.id,
            "date_start": self.start_date,
            "monthly_value": self.monthly_bill_revenue,
            "state": "active",
            "note": (
                f"Generated from Demand Plan '{self.name}'.\n"
                f"Sizing: {self.needed_guards} Guards, {self.needed_supervisors} Supervisors, "
                f"{self.needed_vehicles} Patrol Vehicles, {self.needed_radios} Radios, {self.needed_torches} Torches.\n"
                f"Projected Monthly Gross Profit: ZMW {self.monthly_gross_profit:,.2f} ({self.gross_margin_pct}% Margin)."
            ),
        })

        # 3. Create Contract Rate Card
        self.env["security.contract.rate"].create({
            "contract_id": contract.id,
            "shift_category": "day",
            "rate_type": "hourly",
            "bill_rate": self.bill_rate_per_post_hour,
            "pay_rate": self.guard_monthly_pay / 180.0,
        })

        self.write({
            "state": "converted",
            "converted_contract_id": contract.id,
            "converted_site_id": site.id,
        })

        return {
            "type": "ir.actions.act_window",
            "name": _("Active Client Contract"),
            "res_model": "security.client.contract",
            "res_id": contract.id,
            "view_mode": "form",
            "target": "current",
        }
