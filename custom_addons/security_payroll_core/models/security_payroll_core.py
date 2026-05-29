from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SecurityPayrollPeriod(models.Model):
    _name = "security.payroll.period"
    _description = "Security Payroll Period"
    _order = "date_from desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    rule_set_id = fields.Many2one(
        "security.payroll.rule.set",
        required=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("processed", "Processed"),
            ("closed", "Closed"),
        ],
        default="draft",
        required=True,
    )
    payslip_ids = fields.One2many(
        "security.payslip",
        "period_id",
        string="Payslips",
    )
    payslip_count = fields.Integer(compute="_compute_payslip_count")
    total_earnings = fields.Float(compute="_compute_period_totals")
    total_deductions = fields.Float(compute="_compute_period_totals")
    total_net_pay = fields.Float(compute="_compute_period_totals")
    note = fields.Text()

    @api.depends("date_from", "date_to")
    def _compute_name(self):
        for period in self:
            if period.date_from and period.date_to:
                period.name = f"{period.date_from} to {period.date_to}"
            else:
                period.name = "New Payroll Period"

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for period in self:
            if period.date_to < period.date_from:
                raise ValidationError("Payroll period end date cannot be earlier than start date.")

    def _compute_payslip_count(self):
        for period in self:
            period.payslip_count = len(period.payslip_ids)

    @api.depends("payslip_ids.total_earnings", "payslip_ids.total_deductions", "payslip_ids.net_pay")
    def _compute_period_totals(self):
        for period in self:
            period.total_earnings = sum(period.payslip_ids.mapped("total_earnings"))
            period.total_deductions = sum(period.payslip_ids.mapped("total_deductions"))
            period.total_net_pay = sum(period.payslip_ids.mapped("net_pay"))

    def action_generate_payslips(self):
        attendance_model = self.env["security.attendance.record"]
        payslip_model = self.env["security.payslip"]
        for period in self:
            attendance_records = attendance_model.search(
                [
                    ("shift_date", ">=", period.date_from),
                    ("shift_date", "<=", period.date_to),
                    ("employee_id", "!=", False),
                ]
            )
            employees = attendance_records.mapped("employee_id")
            if not employees:
                raise ValidationError("No attendance records found for this payroll period.")
            for employee in employees:
                payslip = payslip_model.search(
                    [
                        ("period_id", "=", period.id),
                        ("employee_id", "=", employee.id),
                    ],
                    limit=1,
                )
                if not payslip:
                    payslip = payslip_model.create(
                        {
                            "period_id": period.id,
                            "employee_id": employee.id,
                        }
                    )
                payslip.action_compute_from_sources()
            period.state = "processed"

    def action_close(self):
        for period in self:
            period.state = "closed"

    def action_reset_to_draft(self):
        for period in self:
            period.state = "draft"


class SecurityPayslip(models.Model):
    _name = "security.payslip"
    _description = "Security Payslip"
    _order = "period_id desc, employee_id"

    name = fields.Char(compute="_compute_name", store=True)
    period_id = fields.Many2one(
        "security.payroll.period",
        required=True,
        ondelete="cascade",
    )
    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        domain=[("security_guard", "=", True)],
    )
    currency_id = fields.Many2one(
        related="period_id.rule_set_id.currency_id",
        store=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("paid", "Paid"),
        ],
        default="draft",
        required=True,
    )
    attendance_record_ids = fields.Many2many(
        "security.attendance.record",
        "security_payslip_attendance_rel",
        "payslip_id",
        "attendance_id",
        string="Attendance Records",
    )
    leave_request_ids = fields.Many2many(
        "security.leave.request",
        "security_payslip_leave_rel",
        "payslip_id",
        "leave_request_id",
        string="Leave Requests",
    )
    earning_line_ids = fields.One2many(
        "security.payslip.earning.line",
        "payslip_id",
        string="Earning Lines",
    )
    deduction_line_ids = fields.One2many(
        "security.payslip.deduction.line",
        "payslip_id",
        string="Deduction Lines",
    )
    worked_days = fields.Float(
        compute="_compute_period_metrics",
        store=True,
    )
    paid_leave_days = fields.Float(
        compute="_compute_period_metrics",
        store=True,
    )
    unpaid_leave_days = fields.Float(
        compute="_compute_period_metrics",
        store=True,
    )
    late_occurrences = fields.Integer(
        compute="_compute_period_metrics",
        store=True,
    )
    early_departure_occurrences = fields.Integer(
        compute="_compute_period_metrics",
        store=True,
    )
    total_earnings = fields.Float(
        compute="_compute_totals",
        store=True,
    )
    total_deductions = fields.Float(
        compute="_compute_totals",
        store=True,
    )
    net_pay = fields.Float(
        compute="_compute_totals",
        store=True,
    )
    normal_hours = fields.Float(compute="_compute_period_metrics", store=True)
    sunday_hours = fields.Float(compute="_compute_period_metrics", store=True)
    public_holiday_hours = fields.Float(compute="_compute_period_metrics", store=True)
    overtime_hours = fields.Float(compute="_compute_period_metrics", store=True)
    unpaid_hours = fields.Float(compute="_compute_period_metrics", store=True)
    awol_occurrences = fields.Integer(compute="_compute_period_metrics", store=True)
    hourly_rate = fields.Float(compute="_compute_hourly_rate", store=True)
    note = fields.Text()

    @api.depends("employee_id", "period_id")
    def _compute_name(self):
        for payslip in self:
            employee = payslip.employee_id.name or ""
            period = payslip.period_id.name or ""
            payslip.name = f"{employee} - {period}".strip(" -")

    @api.depends(
        "attendance_record_ids.status",
        "attendance_record_ids.payable_hours",
        "attendance_record_ids.overtime_hours",
        "attendance_record_ids.unpaid_hours",
        "attendance_record_ids.premium_category",
        "attendance_record_ids.absence_type",
        "leave_request_ids.requested_days",
        "leave_request_ids.leave_type_id",
    )
    def _compute_period_metrics(self):
        for payslip in self:
            worked_days = 0.0
            late = 0
            early = 0
            paid_leave = 0.0
            unpaid_leave = 0.0
            normal_hours = 0.0
            sunday_hours = 0.0
            public_holiday_hours = 0.0
            overtime_hours = 0.0
            unpaid_hours = 0.0
            awol_occurrences = 0

            for attendance in payslip.attendance_record_ids:
                if attendance.status in ("present", "late", "early_leave"):
                    worked_days += 1.0
                if attendance.status == "late":
                    late += 1
                if attendance.status == "early_leave":
                    early += 1
                if attendance.premium_category == "public_holiday":
                    public_holiday_hours += attendance.payable_hours
                elif attendance.premium_category == "sunday":
                    sunday_hours += attendance.payable_hours
                else:
                    normal_hours += attendance.payable_hours
                overtime_hours += attendance.overtime_hours
                unpaid_hours += attendance.unpaid_hours
                if attendance.absence_type == "awol":
                    awol_occurrences += 1

            for leave_request in payslip.leave_request_ids:
                if leave_request.leave_type_id.code and leave_request.leave_type_id.code.upper() == "UNPAID":
                    unpaid_leave += leave_request.requested_days
                else:
                    paid_leave += leave_request.requested_days

            payslip.worked_days = worked_days
            payslip.paid_leave_days = paid_leave
            payslip.unpaid_leave_days = unpaid_leave
            payslip.late_occurrences = late
            payslip.early_departure_occurrences = early
            payslip.normal_hours = normal_hours
            payslip.sunday_hours = sunday_hours
            payslip.public_holiday_hours = public_holiday_hours
            payslip.overtime_hours = overtime_hours
            payslip.unpaid_hours = unpaid_hours
            payslip.awol_occurrences = awol_occurrences

    @api.depends("employee_id.security_effective_hourly_rate")
    def _compute_hourly_rate(self):
        for payslip in self:
            payslip.hourly_rate = payslip.employee_id.security_effective_hourly_rate

    @api.depends("earning_line_ids.amount", "deduction_line_ids.amount")
    def _compute_totals(self):
        for payslip in self:
            payslip.total_earnings = sum(payslip.earning_line_ids.mapped("amount"))
            payslip.total_deductions = sum(payslip.deduction_line_ids.mapped("amount"))
            payslip.net_pay = payslip.total_earnings - payslip.total_deductions

    def action_confirm(self):
        for payslip in self:
            payslip.state = "confirmed"

    def action_mark_paid(self):
        for payslip in self:
            payslip.state = "paid"

    def action_reset_to_draft(self):
        for payslip in self:
            payslip.state = "draft"

    def action_compute_from_sources(self):
        attendance_model = self.env["security.attendance.record"]
        loan_model = self.env["security.employee.loan"] if "security.employee.loan" in self.env else False
        incident_model = self.env["security.incident"] if "security.incident" in self.env else False
        for payslip in self:
            if not payslip.employee_id or not payslip.period_id:
                continue
            attendance_records = attendance_model.search(
                [
                    ("employee_id", "=", payslip.employee_id.id),
                    ("shift_date", ">=", payslip.period_id.date_from),
                    ("shift_date", "<=", payslip.period_id.date_to),
                ]
            )
            payslip.attendance_record_ids = [(6, 0, attendance_records.ids)]
            payslip._compute_period_metrics()
            payslip._compute_hourly_rate()
            payslip.earning_line_ids.unlink()
            payslip.deduction_line_ids.unlink()

            rate = payslip.hourly_rate
            rule_set = payslip.period_id.rule_set_id
            earning_lines = []
            if payslip.normal_hours:
                earning_lines.append((0, 0, {
                    "name": "Normal Hours",
                    "code": "NORMAL",
                    "quantity": payslip.normal_hours,
                    "rate": rate,
                    "amount": payslip.normal_hours * rate,
                }))
            if payslip.sunday_hours:
                sunday_rate = rate * rule_set.sunday_multiplier
                earning_lines.append((0, 0, {
                    "name": "Sunday Hours",
                    "code": "SUNDAY",
                    "quantity": payslip.sunday_hours,
                    "rate": sunday_rate,
                    "amount": payslip.sunday_hours * sunday_rate,
                }))
            if payslip.public_holiday_hours:
                holiday_rate = rate * rule_set.public_holiday_multiplier
                earning_lines.append((0, 0, {
                    "name": "Public Holiday Hours",
                    "code": "PUBLIC_HOLIDAY",
                    "quantity": payslip.public_holiday_hours,
                    "rate": holiday_rate,
                    "amount": payslip.public_holiday_hours * holiday_rate,
                }))
            if payslip.overtime_hours:
                overtime_rate = rate * rule_set.overtime_multiplier
                earning_lines.append((0, 0, {
                    "name": "Approved Overtime",
                    "code": "OVERTIME",
                    "quantity": payslip.overtime_hours,
                    "rate": overtime_rate,
                    "amount": payslip.overtime_hours * overtime_rate,
                }))
            payslip.earning_line_ids = earning_lines

            deduction_lines = []
            if payslip.unpaid_hours:
                deduction_lines.append((0, 0, {
                    "name": "No Work No Pay Hours",
                    "code": "NO_WORK_NO_PAY",
                    "quantity": payslip.unpaid_hours,
                    "rate": rate,
                    "amount": payslip.unpaid_hours * rate,
                }))
            if loan_model:
                active_loans = loan_model.search(
                    [
                        ("employee_id", "=", payslip.employee_id.id),
                        ("state", "=", "active"),
                        ("balance_remaining", ">", 0),
                    ]
                )
                for loan in active_loans:
                    amount = min(loan.installment_amount, loan.balance_remaining)
                    if amount > 0:
                        deduction_lines.append((0, 0, {
                            "name": f"Loan Deduction - {loan.name}",
                            "code": "LOAN",
                            "quantity": 1.0,
                            "rate": amount,
                            "amount": amount,
                        }))
            if incident_model:
                incidents = incident_model.search(
                    [
                        ("employee_id", "=", payslip.employee_id.id),
                        ("incident_date", ">=", payslip.period_id.date_from),
                        ("incident_date", "<=", payslip.period_id.date_to),
                        ("state", "=", "approved"),
                        ("deduction_amount", ">", 0),
                    ]
                )
                for incident in incidents:
                    deduction_lines.append((0, 0, {
                        "name": f"Incident Deduction - {incident.incident_type_id.name}",
                        "code": "INCIDENT",
                        "quantity": 1.0,
                        "rate": incident.deduction_amount,
                        "amount": incident.deduction_amount,
                    }))
            payslip.deduction_line_ids = deduction_lines


class SecurityPayslipEarningLine(models.Model):
    _name = "security.payslip.earning.line"
    _description = "Security Payslip Earning Line"
    _order = "sequence, id"

    payslip_id = fields.Many2one(
        "security.payslip",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    code = fields.Char()
    quantity = fields.Float(default=1.0)
    rate = fields.Float(default=0.0)
    amount = fields.Float(required=True, default=0.0)


class SecurityPayslipDeductionLine(models.Model):
    _name = "security.payslip.deduction.line"
    _description = "Security Payslip Deduction Line"
    _order = "sequence, id"

    payslip_id = fields.Many2one(
        "security.payslip",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    code = fields.Char()
    quantity = fields.Float(default=1.0)
    rate = fields.Float(default=0.0)
    amount = fields.Float(required=True, default=0.0)
