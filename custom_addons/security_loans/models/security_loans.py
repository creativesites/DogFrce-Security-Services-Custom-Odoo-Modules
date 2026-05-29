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
            ("active", "Active"),
            ("closed", "Closed"),
        ],
        default="draft",
        required=True,
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

    def action_activate(self):
        for loan in self:
            loan.state = "active"

    def action_close(self):
        for loan in self:
            loan.state = "closed"

    def action_reset_to_draft(self):
        for loan in self:
            loan.state = "draft"


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
