from datetime import date

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestLoanAccessControl(TransactionCase):
    """Regression gate for the loan ACL defect documented in
    docs/PRODUCTION_READINESS_AUDIT.md §7.1.

    security.employee.loan has the same defect as security.payslip: full
    CRUD, including unlink, granted to hr.group_hr_user with no record
    rule, and group_security_supervisor implies hr.group_hr_user. A field
    supervisor can currently read, edit and delete any employee's loan
    record — including its principal amount and repayment schedule.

    These tests encode the required behaviour and are expected to FAIL
    until fixed. See docs/PRODUCTION_READINESS_CHECKLIST.md section A1.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_a = cls._create_internal_user("loan-guard-a@access-control.test", "Loan Guard A")
        cls.user_b = cls._create_internal_user("loan-guard-b@access-control.test", "Loan Guard B")

        cls.employee_a = cls.env["hr.employee"].create({
            "name": "Loan Guard A",
            "security_guard": True,
            "user_id": cls.user_a.id,
        })
        cls.employee_b = cls.env["hr.employee"].create({
            "name": "Loan Guard B",
            "security_guard": True,
            "user_id": cls.user_b.id,
        })

        cls.loan_b = cls.env["security.employee.loan"].create({
            "employee_id": cls.employee_b.id,
            "principal_amount": 5000.0,
            "repayment_months": 5,
            "start_date": date(2026, 1, 1),
        })

        cls.supervisor_user = cls._create_internal_user(
            "loan-supervisor@access-control.test", "Loan Test Supervisor"
        )
        cls.supervisor_user.write({
            "group_ids": [(4, cls.env.ref("security_base.group_security_supervisor").id)],
        })

    @classmethod
    def _create_internal_user(cls, login, name):
        return cls.env["res.users"].create({
            "name": name,
            "login": login,
            "email": login,
            "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
        })

    def test_supervisor_cannot_read_other_employees_loan(self):
        with self.assertRaises(AccessError, msg=(
            "A supervisor was able to read another employee's loan "
            "principal_amount. See PRODUCTION_READINESS_AUDIT.md section 7.1."
        )):
            self.loan_b.with_user(self.supervisor_user).read(["principal_amount"])

    def test_supervisor_cannot_write_other_employees_loan(self):
        with self.assertRaises(AccessError, msg=(
            "A supervisor was able to change another employee's loan amount."
        )):
            self.loan_b.with_user(self.supervisor_user).write({"principal_amount": 999999.0})

    def test_supervisor_cannot_unlink_other_employees_loan(self):
        with self.assertRaises(AccessError, msg=(
            "A supervisor was able to delete another employee's loan record."
        )):
            self.loan_b.with_user(self.supervisor_user).unlink()

    def test_payroll_officer_can_still_administer_all_loans(self):
        payroll_officer = self._create_internal_user(
            "loan-payroll-officer@access-control.test", "Loan Payroll Officer"
        )
        payroll_officer.write({
            "group_ids": [(4, self.env.ref(
                "security_base.group_security_hr_payroll_officer"
            ).id)],
        })
        # Should not raise.
        self.loan_b.with_user(payroll_officer).read(["principal_amount"])
