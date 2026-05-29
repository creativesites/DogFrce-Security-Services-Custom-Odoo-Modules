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
            if request.date_from and request.date_to and request.date_to >= request.date_from:
                request.requested_days = float((request.date_to - request.date_from).days + 1)

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
        for request in self:
            balance = request.balance_id
            if not balance:
                balance = self.env["security.leave.balance"].create(
                    {
                        "employee_id": request.employee_id.id,
                        "leave_type_id": request.leave_type_id.id,
                        "balance_days": 0.0,
                    }
                )
                request.balance_id = balance
            balance.balance_days -= request.requested_days
            request.state = "approved"

    def action_refuse(self):
        for request in self:
            request.state = "refused"

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
