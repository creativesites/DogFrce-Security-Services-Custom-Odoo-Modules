from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPayslipAccessControl(TransactionCase):
    """Regression gate for the payroll ACL defect documented in
    docs/PRODUCTION_READINESS_AUDIT.md §7.1.

    security.payslip currently grants full CRUD, including unlink, to
    hr.group_hr_user via ir.model.access.csv, with no record rule
    narrowing it — and group_security_supervisor implies hr.group_hr_user
    (security_base/security/security_groups.xml). The practical result is
    that every field supervisor can read, edit and delete every other
    employee's payslip, including management's.

    These tests encode the required behaviour, not the current one, and
    are expected to FAIL until that defect is fixed. Do not loosen an
    assertion here to make it pass — narrow the actual ACL/record rule
    instead. See docs/PRODUCTION_READINESS_CHECKLIST.md section A1.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.rule_set = cls.env["security.payroll.rule.set"].search(
            [("country_code", "=", "NA")], limit=1
        )
        if not cls.rule_set:
            cls.rule_set = cls.env["security.payroll.rule.set"].create({
                "name": "Access Control Test Rule Set",
                "country_code": "NA",
                "currency_id": cls.env.ref("base.NAD").id,
                "effective_from": "2024-01-01",
                "employee_ssc_rate": 0.009,
                "employer_ssc_rate": 0.009,
                "ssc_salary_cap": 9000.0,
                "sunday_multiplier": 1.0,
                "public_holiday_multiplier": 1.0,
                "saturday_multiplier": 1.0,
                "overtime_multiplier": 1.0,
            })

        cls.period = cls.env["security.payroll.period"].create({
            "name": "Access Control Test Period",
            "date_from": "2026-06-01",
            "date_to": "2026-06-30",
            "rule_set_id": cls.rule_set.id,
        })

        # Two unrelated guards, each linked to their own user — neither
        # is a supervisor and neither should ever see the other's pay.
        cls.user_a = cls._create_internal_user("guard-a@access-control.test", "Guard A User")
        cls.user_b = cls._create_internal_user("guard-b@access-control.test", "Guard B User")

        cls.employee_a = cls.env["hr.employee"].create({
            "name": "Guard A",
            "security_guard": True,
            "user_id": cls.user_a.id,
        })
        cls.employee_b = cls.env["hr.employee"].create({
            "name": "Guard B",
            "security_guard": True,
            "user_id": cls.user_b.id,
        })

        cls.payslip_a = cls.env["security.payslip"].create({
            "period_id": cls.period.id,
            "employee_id": cls.employee_a.id,
        })
        cls.payslip_b = cls.env["security.payslip"].create({
            "period_id": cls.period.id,
            "employee_id": cls.employee_b.id,
        })

        # A supervisor who is neither Guard A nor Guard B, holding only
        # the supervisor group — the group that currently implies
        # hr.group_hr_user and, through it, full payslip CRUD.
        cls.supervisor_user = cls._create_internal_user(
            "supervisor@access-control.test", "Test Supervisor"
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

    # ── The core regression: a supervisor and another employee's payslip ──

    def test_supervisor_cannot_read_other_employees_payslip(self):
        with self.assertRaises(AccessError, msg=(
            "A supervisor was able to read another employee's payslip "
            "(net_pay). See PRODUCTION_READINESS_AUDIT.md section 7.1."
        )):
            self.payslip_b.with_user(self.supervisor_user).read(["net_pay"])

    def test_supervisor_cannot_write_other_employees_payslip(self):
        with self.assertRaises(AccessError, msg=(
            "A supervisor was able to change the state of another "
            "employee's payslip."
        )):
            self.payslip_b.with_user(self.supervisor_user).write({"state": "confirmed"})

    def test_supervisor_cannot_unlink_other_employees_payslip(self):
        with self.assertRaises(AccessError, msg=(
            "A supervisor was able to delete another employee's payslip."
        )):
            self.payslip_b.with_user(self.supervisor_user).unlink()

    # ── The fix must not overcorrect into locking out payroll staff ──

    def test_payroll_officer_can_still_administer_all_payslips(self):
        """A genuine payroll role must still be able to see and process
        every employee's payslip — the fix is narrowing who gets that
        access, not removing the access itself."""
        payroll_officer = self._create_internal_user(
            "payroll-officer@access-control.test", "Payroll Officer"
        )
        payroll_officer.write({
            "group_ids": [(4, self.env.ref(
                "security_base.group_security_hr_payroll_officer"
            ).id)],
        })
        # Should not raise for either employee's payslip.
        self.payslip_a.with_user(payroll_officer).read(["net_pay"])
        self.payslip_b.with_user(payroll_officer).read(["net_pay"])

    def test_owner_can_still_administer_all_payslips(self):
        """The Owner role is the ultimate escalation path (implied_ids
        chain: owner -> manager -> supervisor) and must retain full
        payroll oversight regardless of how the supervisor-level defect
        is fixed."""
        owner_user = self._create_internal_user("owner@access-control.test", "Test Owner")
        owner_user.write({
            "group_ids": [(4, self.env.ref("security_base.group_security_owner").id)],
        })
        self.payslip_a.with_user(owner_user).read(["net_pay"])
        self.payslip_b.with_user(owner_user).read(["net_pay"])
