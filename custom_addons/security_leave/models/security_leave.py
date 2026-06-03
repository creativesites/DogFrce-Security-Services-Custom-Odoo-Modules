from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SecurityLeaveType(models.Model):
    _name = "security.leave.type"
    _description = "Security Leave Type"
    _order = "name"

    name = fields.Char(required=True)
    code = fields.Char()
    active = fields.Boolean(default=True)
    worked_time_based = fields.Boolean(default=False)
    negative_balance_limit = fields.Float(default=0.0)
    accrual_rule_note = fields.Text()

    # Accrual configuration fields.
    # When accrual_method = 'worked_time', the monthly cron calculates:
    #   earned_days = floor(worked_days / accrual_denominator) * accrual_rate
    # Example: 1.25 days per 17 worked days → rate=1.25, denominator=17
    accrual_method = fields.Selection(
        [
            ("manual", "Manual (no auto-accrual)"),
            ("worked_time", "Based on Worked Days"),
        ],
        default="manual",
        required=True,
        string="Accrual Method",
    )
    accrual_rate = fields.Float(
        default=0.0,
        string="Days Earned",
        help="Leave days earned per accrual denominator of worked days.",
    )
    accrual_denominator = fields.Float(
        default=17.0,
        string="Per Worked Days",
        help="Number of worked days required to earn accrual_rate leave days.",
    )
    annual_cap_days = fields.Float(
        default=0.0,
        string="Annual Balance Cap (days)",
        help="Maximum leave balance allowed. 0 means no cap.",
    )

    # G-6: Year-end carryover policy
    carryover_policy = fields.Selection(
        [
            ("carry", "Carry Over"),
            ("forfeit", "Forfeit Unused"),
            ("payout", "Pay Out at Hourly Rate"),
        ],
        default="carry",
        string="Year-End Carryover Policy",
    )
    max_carryover_days = fields.Float(
        default=0.0,
        string="Max Carry-Over Days",
        help="Maximum days that can be carried into the new year. 0 = unlimited carry. Only used when policy is 'Carry Over'.",
    )

    @api.model
    def action_cron_accrue_leave(self):
        """
        Monthly cron: accrue worked-time-based leave for all active guards.

        For each leave type with accrual_method = 'worked_time':
          1. Find all active guards.
          2. Count attendance records in the previous calendar month with
             status in (present, late, early_leave) — each counts as 1 worked day.
          3. earned_days = floor(worked_days / denominator) * accrual_rate
          4. Add earned_days to the guard's balance, capped at annual_cap if set.
        """
        import math
        from datetime import timedelta

        today = fields.Date.context_today(self)
        # Previous month range
        first_of_this_month = today.replace(day=1)
        last_of_prev_month = first_of_this_month - timedelta(days=1)
        first_of_prev_month = last_of_prev_month.replace(day=1)

        accrual_types = self.search(
            [("accrual_method", "=", "worked_time"), ("active", "=", True)]
        )
        if not accrual_types:
            return

        attendance_model = self.env["security.attendance.record"]
        balance_model = self.env["security.leave.balance"]
        employee_model = self.env["hr.employee"]

        active_guards = employee_model.search(
            [("security_guard", "=", True), ("active", "=", True)]
        )

        for leave_type in accrual_types:
            if not leave_type.accrual_rate or not leave_type.accrual_denominator:
                continue
            for employee in active_guards:
                worked_days = attendance_model.search_count(
                    [
                        ("employee_id", "=", employee.id),
                        ("shift_date", ">=", first_of_prev_month),
                        ("shift_date", "<=", last_of_prev_month),
                        ("status", "in", ["present", "late", "early_leave"]),
                    ]
                )
                if not worked_days:
                    continue

                earned = math.floor(worked_days / leave_type.accrual_denominator) * leave_type.accrual_rate
                if earned <= 0:
                    continue

                balance = balance_model.search(
                    [
                        ("employee_id", "=", employee.id),
                        ("leave_type_id", "=", leave_type.id),
                    ],
                    limit=1,
                )
                if not balance:
                    balance = balance_model.create(
                        {
                            "employee_id": employee.id,
                            "leave_type_id": leave_type.id,
                            "balance_days": 0.0,
                        }
                    )

                new_balance = balance.balance_days + earned
                if leave_type.annual_cap_days > 0:
                    new_balance = min(new_balance, leave_type.annual_cap_days)
                balance.balance_days = new_balance

    @api.model
    def action_cron_year_end_carryover(self):
        """
        Year-end cron (run on 1 Jan): apply carryover policy to all balances.
        - carry: cap balance at max_carryover_days (0 = no cap)
        - forfeit: zero out the balance
        - payout: create a payslip earning note (log only — payroll officer must act)
        """
        leave_types = self.search([("carryover_policy", "!=", False)])
        balance_model = self.env["security.leave.balance"]
        for lt in leave_types:
            balances = balance_model.search([("leave_type_id", "=", lt.id)])
            for bal in balances:
                if lt.carryover_policy == "forfeit":
                    bal.balance_days = 0.0
                elif lt.carryover_policy == "carry" and lt.max_carryover_days > 0:
                    bal.balance_days = min(bal.balance_days, lt.max_carryover_days)
                elif lt.carryover_policy == "payout":
                    # Log the payout amount for the payroll officer to action
                    if bal.balance_days > 0:
                        if "security.notification" in self.env:
                            self.env["security.notification"].sudo().create({
                                "title": f"Leave Encashment Required: {bal.employee_id.name}",
                                "body": f"{bal.employee_id.name} has {bal.balance_days:.1f} unused {lt.name} days to be paid out at year-end.",
                                "notification_type": "system",
                                "severity": "info",
                            })
                        bal.balance_days = 0.0


class SecurityLeaveBalance(models.Model):
    _name = "security.leave.balance"
    _description = "Security Leave Balance"
    _order = "employee_id, leave_type_id"

    _security_leave_balance_unique = models.Constraint(
        "UNIQUE(employee_id, leave_type_id)",
        "There can only be one leave balance per employee and leave type.",
    )

    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        domain=[("security_guard", "=", True)],
    )
    leave_type_id = fields.Many2one("security.leave.type", required=True)
    balance_days = fields.Float(default=0.0)
    note = fields.Text()


class SecurityLeaveRequest(models.Model):
    _name = "security.leave.request"
    _description = "Security Leave Request"
    _order = "date_from desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        domain=[("security_guard", "=", True)],
    )
    leave_type_id = fields.Many2one("security.leave.type", required=True)
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    requested_days = fields.Float(
        compute="_compute_requested_days",
        store=True,
    )
    # G-7: public holidays excluded from leave consumption
    public_holidays_excluded = fields.Integer(
        default=0,
        readonly=True,
        string="Public Holidays Excluded",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("approved", "Approved"),
            ("refused", "Refused"),
        ],
        default="draft",
        required=True,
    )
    balance_id = fields.Many2one(
        "security.leave.balance",
        compute="_compute_balance_id",
        store=True,
    )
    remaining_balance_after = fields.Float(
        compute="_compute_remaining_balance_after",
        store=True,
    )
    note = fields.Text()

    @api.depends("employee_id", "leave_type_id")
    def _compute_balance_id(self):
        balance_model = self.env["security.leave.balance"]
        for request in self:
            request.balance_id = balance_model.search(
                [
                    ("employee_id", "=", request.employee_id.id),
                    ("leave_type_id", "=", request.leave_type_id.id),
                ],
                limit=1,
            )

    @api.depends("employee_id", "leave_type_id", "date_from", "date_to")
    def _compute_name(self):
        for request in self:
            employee = request.employee_id.name or ""
            leave_type = request.leave_type_id.name or ""
            request.name = f"{employee} - {leave_type}".strip(" -")

    @api.depends("date_from", "date_to")
    def _compute_requested_days(self):
        for request in self:
            request.requested_days = 0.0
            request.public_holidays_excluded = 0
            if request.date_from and request.date_to and request.date_to >= request.date_from:
                requested_days = float((request.date_to - request.date_from).days + 1)
                # G-7: Exclude public holidays from leave consumption
                if request.date_from and request.date_to:
                    public_holidays = self.env["security.public.holiday"].search([
                        ("date", ">=", request.date_from),
                        ("date", "<=", request.date_to),
                    ])
                    holiday_count = len(public_holidays)
                    requested_days = max(0, requested_days - holiday_count)
                    request.requested_days = requested_days
                    if holiday_count:
                        request.public_holidays_excluded = holiday_count
                else:
                    request.requested_days = requested_days

    @api.depends("balance_id.balance_days", "requested_days", "state")
    def _compute_remaining_balance_after(self):
        for request in self:
            current_balance = request.balance_id.balance_days if request.balance_id else 0.0
            if request.state == "approved":
                request.remaining_balance_after = current_balance - request.requested_days
            else:
                request.remaining_balance_after = current_balance

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for request in self:
            if request.date_to < request.date_from:
                raise ValidationError("Leave end date cannot be earlier than start date.")

    @api.constrains("employee_id", "leave_type_id", "requested_days", "state")
    def _check_negative_limit(self):
        for request in self:
            if request.state != "approved":
                continue
            balance = request.balance_id.balance_days if request.balance_id else 0.0
            limit = request.leave_type_id.negative_balance_limit
            if balance - request.requested_days < (-1 * limit):
                raise ValidationError(
                    "The approved leave request would exceed the allowed negative balance limit."
                )

    def action_approve(self):
        for leave in self:
            balance = leave.balance_id
            if not balance:
                balance = self.env["security.leave.balance"].create(
                    {
                        "employee_id": leave.employee_id.id,
                        "leave_type_id": leave.leave_type_id.id,
                        "balance_days": 0.0,
                    }
                )
                leave.balance_id = balance
            balance.balance_days -= leave.requested_days
            leave.state = "approved"
            # I-5: create notification for operations supervisor
            if "security.notification" in self.env:
                self.env["security.notification"].sudo().create({
                    "title": f"Leave Approved: {leave.employee_id.name}",
                    "body": (
                        f"{leave.employee_id.name} has been approved for "
                        f"{leave.leave_type_id.name} leave from {leave.date_from} to {leave.date_to} "
                        f"({leave.requested_days:.1f} days). Ensure roster coverage is arranged."
                    ),
                    "notification_type": "system",
                    "severity": "info",
                })

    def action_refuse(self):
        for leave in self:
            leave.state = "refused"
            # I-5: create notification for operations supervisor
            if "security.notification" in self.env:
                self.env["security.notification"].sudo().create({
                    "title": f"Leave Refused: {leave.employee_id.name}",
                    "body": f"Leave request for {leave.employee_id.name} ({leave.leave_type_id.name}) was refused.",
                    "notification_type": "system",
                    "severity": "info",
                })

    def action_reset_to_draft(self):
        for request in self:
            request.state = "draft"


class SecurityRosterSlot(models.Model):
    _inherit = "security.roster.slot"

    leave_request_id = fields.Many2one(
        "security.leave.request",
        compute="_compute_leave_request_id",
        store=True,
    )

    @api.depends("employee_id", "shift_date")
    def _compute_leave_request_id(self):
        leave_model = self.env["security.leave.request"]
        for slot in self:
            slot.leave_request_id = leave_model.search(
                [
                    ("employee_id", "=", slot.employee_id.id),
                    ("state", "=", "approved"),
                    ("date_from", "<=", slot.shift_date),
                    ("date_to", ">=", slot.shift_date),
                ],
                limit=1,
            )

    @api.constrains("employee_id", "shift_date", "leave_request_id")
    def _check_approved_leave_conflict(self):
        for slot in self:
            if slot.employee_id and slot.leave_request_id:
                raise ValidationError(
                    "A guard with approved leave cannot be assigned to a roster slot on that date."
                )
