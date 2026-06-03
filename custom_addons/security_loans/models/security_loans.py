from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SecurityEmployeeLoan(models.Model):
    _name = "security.employee.loan"
    _description = "Security Employee Loan"
    _order = "start_date desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        domain=[("security_guard", "=", True)],
    )
    currency_id = fields.Many2one(
        "res.currency",
        required=True,
        default=lambda self: self.env.company.currency_id.id,
    )
    principal_amount = fields.Float(required=True)
    interest_rate = fields.Float(
        default=0.0,
        help="Use a decimal rate such as 0.10 for 10 percent interest.",
    )
    repayment_months = fields.Integer(required=True, default=1)
    start_date = fields.Date(required=True)
    installment_amount = fields.Float(
        compute="_compute_financials",
        store=True,
    )
    total_repayment_amount = fields.Float(
        compute="_compute_financials",
        store=True,
    )
    balance_remaining = fields.Float(
        compute="_compute_balance_remaining",
        store=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("active", "Active"),
            ("closed", "Closed"),
            ("written_off", "Written Off"),
        ],
        default="draft",
        required=True,
    )
    submitted_by_id = fields.Many2one("res.users", readonly=True, string="Submitted By")
    approved_by_id = fields.Many2one("res.users", readonly=True, string="Approved By")
    approval_date = fields.Datetime(readonly=True)
    rejection_reason = fields.Text()
    deduction_priority = fields.Integer(
        default=10,
        string="Deduction Priority",
        help="Lower number = deducted first when multiple loans are active.",
    )
    deduction_line_ids = fields.One2many(
        "security.loan.deduction",
        "loan_id",
        string="Loan Deductions",
    )
    note = fields.Text()

    @api.depends("employee_id", "start_date")
    def _compute_name(self):
        for loan in self:
            employee = loan.employee_id.name or ""
            date = loan.start_date or ""
            loan.name = f"{employee} Loan - {date}".strip(" -")

    @api.depends("principal_amount", "interest_rate", "repayment_months")
    def _compute_financials(self):
        for loan in self:
            total_interest = loan.principal_amount * loan.interest_rate
            loan.total_repayment_amount = loan.principal_amount + total_interest
            if loan.repayment_months > 0:
                loan.installment_amount = loan.total_repayment_amount / loan.repayment_months
            else:
                loan.installment_amount = 0.0

    @api.depends("total_repayment_amount", "deduction_line_ids.amount", "state")
    def _compute_balance_remaining(self):
        for loan in self:
            deducted = sum(loan.deduction_line_ids.mapped("amount"))
            balance = loan.total_repayment_amount - deducted
            loan.balance_remaining = max(balance, 0.0)
            if loan.state == "active" and loan.balance_remaining <= 0:
                loan.state = "closed"

    @api.constrains("principal_amount", "repayment_months")
    def _check_loan_values(self):
        for loan in self:
            if loan.principal_amount <= 0:
                raise ValidationError("Loan principal amount must be greater than zero.")
            if loan.repayment_months <= 0:
                raise ValidationError("Repayment months must be greater than zero.")

    # ── Workflow actions ──────────────────────────────────────────────────────

    def action_submit(self):
        for loan in self:
            if loan.state == "draft":
                loan.state = "submitted"
                loan.submitted_by_id = self.env.user.id

    def action_approve(self):
        for loan in self:
            if loan.state == "submitted":
                loan.state = "approved"
                loan.approved_by_id = self.env.user.id
                loan.approval_date = fields.Datetime.now()

    def action_activate(self):
        for loan in self:
            if loan.state == "approved":
                loan.state = "active"
                # Generate deduction schedule if not already done
                if not loan.deduction_line_ids:
                    loan._generate_deduction_schedule()

    def action_generate_schedule(self):
        for loan in self:
            if not loan.deduction_line_ids:
                loan._generate_deduction_schedule()

    def _generate_deduction_schedule(self):
        self.ensure_one()
        from dateutil.relativedelta import relativedelta
        start = self.start_date
        monthly_amount = self.installment_amount
        for i in range(self.repayment_months):
            deduction_date = start + relativedelta(months=i)
            self.env["security.loan.deduction"].create({
                "loan_id": self.id,
                "deduction_date": deduction_date,
                "amount": monthly_amount,
            })

    def action_write_off(self):
        for loan in self:
            loan.state = "written_off"

    def action_close(self):
        for loan in self:
            loan.state = "closed"

    def action_reset_to_draft(self):
        for loan in self:
            if loan.state in ("draft", "submitted", "approved"):
                loan.state = "draft"

    def action_apply_carry_forward(self):
        """Called by payroll after capping — adds carry-forward to the next deduction line."""
        for loan in self:
            carry = sum(loan.deduction_line_ids.filtered("capped").mapped("carry_forward_amount"))
            if carry <= 0:
                continue
            next_line = loan.deduction_line_ids.filtered(
                lambda l: not l.payslip_id and not l.capped
            ).sorted("deduction_date")[:1]
            if next_line:
                next_line.amount += carry


class SecurityLoanDeduction(models.Model):
    _name = "security.loan.deduction"
    _description = "Security Loan Deduction"
    _order = "deduction_date desc, id desc"

    loan_id = fields.Many2one(
        "security.employee.loan",
        required=True,
        ondelete="cascade",
    )
    employee_id = fields.Many2one(
        related="loan_id.employee_id",
        store=True,
    )
    payslip_id = fields.Many2one(
        "security.payslip",
        ondelete="set null",
    )
    deduction_date = fields.Date(required=True)
    amount = fields.Float(required=True)
    note = fields.Text()
    carry_forward_amount = fields.Float(
        default=0.0,
        string="Capped Amount (Carry Forward)",
        help="Amount that could not be deducted this period due to the net pay floor cap. Will be added to the next period's deduction.",
    )
    capped = fields.Boolean(default=False, readonly=True, string="Was Capped This Period")

    @api.constrains("amount")
    def _check_amount(self):
        for deduction in self:
            if deduction.amount <= 0:
                raise ValidationError("Loan deduction amount must be greater than zero.")


class SecurityPayslip(models.Model):
    _inherit = "security.payslip"

    loan_deduction_ids = fields.Many2many(
        "security.loan.deduction",
        "security_payslip_loan_deduction_rel",
        "payslip_id",
        "loan_deduction_id",
        string="Loan Deductions",
    )
