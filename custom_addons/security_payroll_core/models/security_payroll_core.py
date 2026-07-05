import base64

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

    def action_recompute_payslips(self):
        self.action_generate_payslips()

    def action_confirm_payslips(self):
        for period in self:
            period.payslip_ids.filtered(lambda payslip: payslip.state == "draft").action_confirm()

    def action_mark_payslips_paid(self):
        for period in self:
            period.payslip_ids.filtered(lambda payslip: payslip.state == "confirmed").action_mark_paid()

    def action_print_payslips(self):
        self.ensure_one()
        if not self.payslip_ids:
            raise ValidationError("There are no payslips in this period to print.")
        return self.env.ref("security_payroll_core.action_report_security_payslip").report_action(self.payslip_ids)

    def action_close(self):
        for period in self:
            period.state = "closed"

    def action_reset_to_draft(self):
        for period in self:
            period.state = "draft"

    def action_email_payslips(self):
        self.ensure_one()
        sent = 0
        failed = 0
        for payslip in self.payslip_ids.filtered(lambda p: p.state in ("confirmed", "paid")):
            employee = payslip.employee_id
            email_to = employee.work_email
            if not email_to:
                failed += 1
                continue
            try:
                report = self.env.ref("security_payroll_core.action_report_security_payslip")
                pdf_content, _ = report._render_qweb_pdf([payslip.id])
                attachment = self.env["ir.attachment"].create({
                    "name": f"Payslip_{payslip.name.replace('/', '_')}.pdf",
                    "type": "binary",
                    "datas": base64.b64encode(pdf_content),
                    "res_model": "security.payslip",
                    "res_id": payslip.id,
                })
                mail = self.env["mail.mail"].create({
                    "subject": f"Your Payslip — {payslip.name}",
                    "email_to": email_to,
                    "body_html": f"<p>Dear {employee.name},</p><p>Please find your payslip for {payslip.name} attached.</p><p>DogForce Security Services</p>",
                    "attachment_ids": [(4, attachment.id)],
                })
                mail.send()
                sent += 1
            except Exception:
                failed += 1
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Payslips Emailed",
                "message": f"{sent} sent, {failed} failed (no email address).",
                "type": "success" if not failed else "warning",
            },
        }

    def action_export_payroll_register(self):
        self.ensure_one()
        import io
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Employee", "SSC Number", "Tax Number",
            "Normal Hrs", "Sat Hrs", "Sun Hrs", "PH Hrs", "Night Hrs", "OT Hrs",
            "Gross Pay", "SSC Deduction", "PAYE Deduction",
            "Loan Deductions", "Incident Deductions", "Net Pay", "State",
        ])
        for ps in self.payslip_ids.sorted(key=lambda p: p.employee_id.name):
            ssc = sum(ps.deduction_line_ids.filtered(lambda l: l.code == "SSC").mapped("amount"))
            paye = sum(ps.deduction_line_ids.filtered(lambda l: l.code == "PAYE").mapped("amount"))
            loans = sum(ps.deduction_line_ids.filtered(lambda l: l.code == "LOAN").mapped("amount"))
            incidents = sum(ps.deduction_line_ids.filtered(lambda l: l.code == "INCIDENT").mapped("amount"))
            writer.writerow([
                ps.employee_id.name,
                ps.employee_id.security_ssc_number or "",
                ps.employee_id.security_tax_number or "",
                round(ps.normal_hours, 2),
                round(ps.saturday_hours, 2),
                round(ps.sunday_hours, 2),
                round(ps.public_holiday_hours, 2),
                round(ps.night_hours, 2),
                round(ps.overtime_hours, 2),
                round(ps.total_earnings, 2),
                round(ssc, 2),
                round(paye, 2),
                round(loans, 2),
                round(incidents, 2),
                round(ps.net_pay, 2),
                ps.state,
            ])
        csv_bytes = base64.b64encode(output.getvalue().encode("utf-8"))
        attachment = self.env["ir.attachment"].create({
            "name": f"Payroll_Register_{self.name.replace('/', '_')}.csv",
            "type": "binary",
            "datas": csv_bytes,
            "res_model": "security.payroll.period",
            "res_id": self.id,
        })
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }


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
    saturday_hours = fields.Float(compute="_compute_period_metrics", store=True)
    night_hours = fields.Float(compute="_compute_period_metrics", store=True)
    overtime_hours = fields.Float(compute="_compute_period_metrics", store=True)
    unpaid_hours = fields.Float(compute="_compute_period_metrics", store=True)
    awol_occurrences = fields.Integer(compute="_compute_period_metrics", store=True)
    hourly_rate = fields.Float(compute="_compute_hourly_rate", store=True)
    anomaly_flags = fields.Text(readonly=True)
    anomaly_score = fields.Integer(default=0, readonly=True)
    note = fields.Text()

    @api.depends("employee_id", "period_id")
    def _compute_name(self):
        for payslip in self:
            employee = payslip.employee_id.name or ""
            period = payslip.period_id.name or ""
            payslip.name = f"{employee} - {period}".strip(" -")

    @api.depends(
        "attendance_record_ids.status",
        "attendance_record_ids.normal_hours",
        "attendance_record_ids.sunday_hours",
        "attendance_record_ids.public_holiday_hours",
        "attendance_record_ids.saturday_hours",
        "attendance_record_ids.night_hours",
        "attendance_record_ids.overtime_hours",
        "attendance_record_ids.unpaid_hours",
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
            saturday_hours = 0.0
            night_hours = 0.0
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
                normal_hours += attendance.normal_hours
                sunday_hours += attendance.sunday_hours
                public_holiday_hours += attendance.public_holiday_hours
                saturday_hours += attendance.saturday_hours
                night_hours += attendance.night_hours
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
            payslip.saturday_hours = saturday_hours
            payslip.night_hours = night_hours
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
            if payslip.saturday_hours:
                saturday_rate = rate * rule_set.saturday_multiplier
                earning_lines.append((0, 0, {
                    "name": "Saturday Hours",
                    "code": "SATURDAY",
                    "quantity": payslip.saturday_hours,
                    "rate": saturday_rate,
                    "amount": payslip.saturday_hours * saturday_rate,
                }))
            if payslip.night_hours:
                night_rate = rate * rule_set.night_shift_multiplier
                earning_lines.append((0, 0, {
                    "name": "Night Shift Hours",
                    "code": "NIGHT",
                    "quantity": payslip.night_hours,
                    "rate": night_rate,
                    "amount": payslip.night_hours * night_rate,
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

            # Calculate gross earnings from earning lines to use in statutory computations
            gross_earnings = sum(line[2]["amount"] for line in earning_lines)

            deduction_lines = []
            if payslip.unpaid_hours:
                deduction_lines.append((0, 0, {
                    "name": "No Work No Pay Hours",
                    "code": "NO_WORK_NO_PAY",
                    "quantity": payslip.unpaid_hours,
                    "rate": rate,
                    "amount": payslip.unpaid_hours * rate,
                }))

            # 1. Social Security Commission (SSC) Deduction Calculation (Namibia)
            # SSC is calculated on basic wage/salary (Normal + Sunday + Public Holiday hours)
            basic_ssc_base = sum(
                line[2]["amount"]
                for line in earning_lines
                if line[2]["code"] in ("NORMAL", "SUNDAY", "PUBLIC_HOLIDAY", "SATURDAY", "NIGHT")
            )
            ssc_rate = rule_set.employee_ssc_rate or 0.009
            ssc_cap = rule_set.ssc_salary_cap or 9000.0
            ssc_deduction = min(basic_ssc_base, ssc_cap) * ssc_rate
            if ssc_deduction > 0:
                deduction_lines.append((0, 0, {
                    "name": "Social Security Commission (SSC)",
                    "code": "SSC",
                    "quantity": 1.0,
                    "rate": ssc_deduction,
                    "amount": ssc_deduction,
                }))

            # 2. Pay As You Earn (PAYE) Deduction Calculation (Namibia)
            # SSC is tax-deductible in Namibia
            taxable_monthly = max(gross_earnings - ssc_deduction, 0.0)
            annual_taxable_income = taxable_monthly * 12.0

            brackets = self.env["security.tax.bracket"].search(
                [("rule_set_id", "=", rule_set.id)], order="lower_bound"
            )
            paye_deduction = 0.0
            for bracket in brackets:
                upper = bracket.upper_bound or float("inf")
                if bracket.lower_bound <= annual_taxable_income <= upper:
                    lower = int(bracket.lower_bound)
                    annual_tax = bracket.fixed_amount + (
                        (annual_taxable_income - lower) * bracket.rate
                    )
                    paye_deduction = max(annual_tax / 12.0, 0.0)
                    break

            if paye_deduction > 0:
                deduction_lines.append((0, 0, {
                    "name": "Pay As You Earn (PAYE)",
                    "code": "PAYE",
                    "quantity": 1.0,
                    "rate": paye_deduction,
                    "amount": paye_deduction,
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

            # Deduction cap: ensure net pay stays above the configured floor
            floor_pct = rule_set.deduction_floor_pct if rule_set else 0.30
            min_net = payslip.total_earnings * floor_pct
            if payslip.total_deductions > payslip.total_earnings - min_net:
                excess = payslip.total_deductions - (payslip.total_earnings - min_net)
                # Remove excess from the last (lowest-priority) deduction line
                # Sort so LOAN/INCIDENT lines come last (reduced first)
                ded_lines = payslip.deduction_line_ids.sorted(key=lambda l: (l.code not in ('LOAN', 'INCIDENT'), l.id))
                for line in reversed(list(ded_lines)):
                    if excess <= 0:
                        break
                    remove = min(line.amount, excess)
                    line.carry_forward_amount = remove
                    line.amount -= remove
                    line.capped = True
                    excess -= remove
                    if line.amount <= 0:
                        line.unlink()

            # Anomaly detection — surface patterns that warrant review.
            flags = []
            score = 0
            if payslip.awol_occurrences >= 2:
                flags.append(f"AWOL x{payslip.awol_occurrences} — repeated unauthorised absences")
                score += payslip.awol_occurrences * 3
            if payslip.late_occurrences >= 3:
                flags.append(f"Late arrivals x{payslip.late_occurrences}")
                score += payslip.late_occurrences
            missing_checkouts = sum(
                1 for rec in attendance_records if rec.missing_check_out
            )
            if missing_checkouts >= 2:
                flags.append(f"Missing check-out x{missing_checkouts}")
                score += missing_checkouts * 2
            total_payable = (
                payslip.normal_hours
                + payslip.sunday_hours
                + payslip.public_holiday_hours
                + payslip.saturday_hours
                + payslip.night_hours
            )
            if total_payable > 0 and payslip.unpaid_hours / total_payable > 0.35:
                pct = round(payslip.unpaid_hours / total_payable * 100)
                flags.append(f"High no-work-no-pay ratio: {pct}% of scheduled hours unpaid")
                score += 5
            payslip.anomaly_flags = "\n".join(flags) if flags else False
            payslip.anomaly_score = score

    def action_print_payslip(self):
        return self.env.ref("security_payroll_core.action_report_security_payslip").report_action(self)

    def action_preview_payslip(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/report/html/security_payroll_core.report_security_payslip/{self.id}",
            "target": "new",
        }


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
    capped = fields.Boolean(default=False, readonly=True, string="Capped by Floor")
    carry_forward_amount = fields.Float(default=0.0, string="Carry Forward Amount")


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    security_employment_number = fields.Char(string="Employment Number", index=True)
    security_ssc_number = fields.Char(string="SSC Number")
    security_tax_number = fields.Char(string="Income Tax / PAYE Number")
    security_bank_name = fields.Char(string="Bank Name")
    security_bank_branch = fields.Char(string="Bank Branch Code")
    security_bank_account_number = fields.Char(string="Bank Account Number")

    # H-14: payslip history on employee form
    payslip_ids = fields.One2many(
        "security.payslip",
        "employee_id",
        string="Payslips",
    )
    payslip_count = fields.Integer(
        compute="_compute_employee_payslip_count",
        string="Payslip Count",
    )

    def _compute_employee_payslip_count(self):
        for emp in self:
            emp.payslip_count = self.env["security.payslip"].search_count(
                [("employee_id", "=", emp.id)]
            )
