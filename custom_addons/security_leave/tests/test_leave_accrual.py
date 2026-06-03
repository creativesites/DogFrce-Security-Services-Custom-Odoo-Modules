from datetime import date, timedelta
from odoo.tests.common import TransactionCase

class TestLeaveAccrual(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create a leave type with worked-time accrual
        cls.leave_type = cls.env["security.leave.type"].create({
            "name": "Test Annual Leave",
            "accrual_method": "worked_time",
            "accrual_rate": 1.0,
            "accrual_denominator": 22,
        })
        # Create a guard employee
        cls.employee = cls.env["hr.employee"].create({
            "name": "Test Guard Accrual",
            "security_guard": True,
        })
        # Create a leave balance
        cls.balance = cls.env["security.leave.balance"].create({
            "employee_id": cls.employee.id,
            "leave_type_id": cls.leave_type.id,
            "balance_days": 0.0,
        })

    def test_accrual_adds_days_after_22_shifts(self):
        """22 present attendance records → 1 accrued day."""
        # Create 22 present records in the previous month
        prev_month_start = date.today().replace(day=1) - timedelta(days=1)
        prev_month_start = prev_month_start.replace(day=1)
        for i in range(22):
            shift_date = prev_month_start + timedelta(days=i)
            self.env["security.attendance.record"].create({
                "employee_id": self.employee.id,
                "shift_date": shift_date,
                "status": "present",
                "manual_presence": "present",
            })
        # Run accrual cron
        self.env["security.leave.type"].action_cron_accrue_leave()
        # Assert balance increased by 1
        self.balance.invalidate_recordset()
        self.assertAlmostEqual(self.balance.balance_days, 1.0, places=1)

    def test_no_accrual_below_threshold(self):
        """Only 10 present records → no accrual (< 22 required)."""
        employee2 = self.env["hr.employee"].create({
            "name": "Test Guard Low Shifts",
            "security_guard": True,
        })
        balance2 = self.env["security.leave.balance"].create({
            "employee_id": employee2.id,
            "leave_type_id": self.leave_type.id,
            "balance_days": 0.0,
        })
        prev_month_start = date.today().replace(day=1) - timedelta(days=1)
        prev_month_start = prev_month_start.replace(day=1)
        for i in range(10):
            self.env["security.attendance.record"].create({
                "employee_id": employee2.id,
                "shift_date": prev_month_start + timedelta(days=i),
                "status": "present",
                "manual_presence": "present",
            })
        self.env["security.leave.type"].action_cron_accrue_leave()
        balance2.invalidate_recordset()
        self.assertEqual(balance2.balance_days, 0.0)

    def test_manual_leave_type_not_accrued(self):
        """Leave types with accrual_method='manual' are skipped by the cron."""
        manual_type = self.env["security.leave.type"].create({
            "name": "Manual Leave",
            "accrual_method": "manual",
        })
        employee3 = self.env["hr.employee"].create({
            "name": "Test Guard Manual",
            "security_guard": True,
        })
        balance3 = self.env["security.leave.balance"].create({
            "employee_id": employee3.id,
            "leave_type_id": manual_type.id,
            "balance_days": 5.0,
        })
        self.env["security.leave.type"].action_cron_accrue_leave()
        balance3.invalidate_recordset()
        self.assertEqual(balance3.balance_days, 5.0)
