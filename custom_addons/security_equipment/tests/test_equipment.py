from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import date, timedelta


class TestSecurityEquipment(TransactionCase):

    def setUp(self):
        super(TestSecurityEquipment, self).setUp()
        
        # 1. Create access groups and employee
        self.employee = self.env["hr.employee"].create(
            {
                "name": "Nafuka Andreas",
                "security_guard": True,
                "security_effective_hourly_rate": 25.0,
            }
        )

        # 2. Create basic equipment categories and profiles
        self.cat_uniform = self.env["security.equipment.category"].create(
            {
                "name": "Uniforms",
                "code": "UNIFORM",
            }
        )
        self.cat_firearm = self.env["security.equipment.category"].create(
            {
                "name": "Firearms",
                "code": "FIREARM",
            }
        )

        # 3. Create non-serialized and serialized equipment types
        self.type_boots = self.env["security.equipment.type"].create(
            {
                "name": "Standard Combat Boots",
                "category_id": self.cat_uniform.id,
                "is_serialized": False,
                "qty_total": 10,
                "unit_cost": 450.0,
            }
        )
        self.type_pistol = self.env["security.equipment.type"].create(
            {
                "name": "9mm Beretta Pistol",
                "category_id": self.cat_firearm.id,
                "is_serialized": True,
                "requires_license": True,
                "unit_cost": 12000.0,
            }
        )

        # 4. Create serialized items
        self.item_pistol_1 = self.env["security.equipment.item"].create(
            {
                "type_id": self.type_pistol.id,
                "serial_number": "BER-99210",
                "license_number": "LIC-992",
                "condition": "excellent",
                "status": "available",
            }
        )

        # 5. Create a basic payroll ruleset and period for testing deduction injection
        self.currency = self.env.company.currency_id
        self.rule_set = self.env["security.payroll.rule.set"].create(
            {
                "name": "Standard Namibia Ruleset",
                "currency_id": self.currency.id,
                "sunday_multiplier": 2.0,
                "public_holiday_multiplier": 2.0,
                "overtime_multiplier": 1.5,
            }
        )
        self.payroll_period = self.env["security.payroll.period"].create(
            {
                "date_from": date.today() - timedelta(days=15),
                "date_to": date.today() + timedelta(days=15),
                "rule_set_id": self.rule_set.id,
            }
        )

    def test_01_serialized_item_allocation(self):
        """Test serialized allocation flow and availability validation."""
        # 1. Create a draft allocation for the pistol
        alloc = self.env["security.equipment.allocation"].create(
            {
                "employee_id": self.employee.id,
                "equipment_type_id": self.type_pistol.id,
                "equipment_item_id": self.item_pistol_1.id,
                "condition_on_issue": "excellent",
                "quantity": 1.0,
            }
        )
        self.assertEqual(alloc.state, "draft")
        self.assertEqual(self.item_pistol_1.status, "available")

        # 2. Issue the pistol
        alloc.action_issue()
        self.assertEqual(alloc.state, "issued")
        self.assertEqual(self.item_pistol_1.status, "issued")

        # 3. Verify that trying to allocate the same pistol throws validation error
        with self.assertRaises(ValidationError):
            self.env["security.equipment.allocation"].create(
                {
                    "employee_id": self.employee.id,
                    "equipment_type_id": self.type_pistol.id,
                    "equipment_item_id": self.item_pistol_1.id,
                    "quantity": 1.0,
                }
            ).action_issue()

        # 4. Return the pistol and verify status restores
        alloc.condition_on_return = "good"
        alloc.action_return()
        self.assertEqual(alloc.state, "returned")
        self.assertEqual(self.item_pistol_1.status, "available")
        self.assertEqual(self.item_pistol_1.condition, "good")

    def test_02_loss_damage_deduction_flow(self):
        """Test loss logging, inventory status change, and automated payroll deduction."""
        # 1. Issue Pistol to Employee
        alloc = self.env["security.equipment.allocation"].create(
            {
                "employee_id": self.employee.id,
                "equipment_type_id": self.type_pistol.id,
                "equipment_item_id": self.item_pistol_1.id,
                "quantity": 1.0,
            }
        )
        alloc.action_issue()

        # 2. Log loss incident
        damage_log = self.env["security.equipment.damage"].create(
            {
                "allocation_id": alloc.id,
                "incident_type": "loss",
                "description": "Officer reports pistol fell into river during patrol.",
                "cost_repair_replace": 12000.0,
                "deduction_amount": 3000.0,
            }
        )
        self.assertEqual(damage_log.state, "draft")

        # 3. Approve incident and verify automatic condition changes
        damage_log.action_investigate()
        damage_log.action_approve()
        
        self.assertEqual(damage_log.state, "approved")
        self.assertEqual(alloc.state, "lost")
        self.assertEqual(self.item_pistol_1.status, "lost")
        self.assertEqual(self.item_pistol_1.condition, "scrapped")

        # 4. Create a payslip for the employee and compute from sources
        payslip = self.env["security.payslip"].create(
            {
                "period_id": self.payroll_period.id,
                "employee_id": self.employee.id,
            }
        )
        payslip.action_compute_from_sources()

        # 5. Assert that the deduction line is injected correctly
        ded_line = payslip.deduction_line_ids.filtered(lambda l: l.code == "EQUIPMENT_LOSS")
        self.assertTrue(ded_line, "Equipment deduction line was not added to the payslip.")
        self.assertEqual(ded_line.amount, 3000.0)
        self.assertEqual(damage_log.state, "deducted")
        self.assertEqual(damage_log.payslip_id.id, payslip.id)
