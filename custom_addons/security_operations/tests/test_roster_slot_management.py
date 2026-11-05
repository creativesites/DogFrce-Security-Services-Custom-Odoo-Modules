# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError, ValidationError


@tagged("post_install", "-at_install")
class TestRosterSlotManagement(TransactionCase):
    """
    Test suite for dynamic slot management:
    - Auto-spawning slots when guard_count increases
    - Auto-cancelling excess unassigned slots when guard_count decreases
    - Contract sync with operational requirements and roster cycles
    - Slot unassign, cancel, reset to draft, and ad-hoc slot creation
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({
            "name": "Adcon Mining Logistics",
            "is_company": True,
        })
        cls.shift_day = cls.env["security.shift.template"].create({
            "name": "Day Shift 12h",
            "start_hour": 6.0,
            "end_hour": 18.0,
            "duration_hours": 12.0,
        })
        cls.shift_night = cls.env["security.shift.template"].create({
            "name": "Night Shift 12h",
            "start_hour": 18.0,
            "end_hour": 6.0,
            "duration_hours": 12.0,
        })
        cls.grade_a = cls.env["security.grade"].create({
            "name": "Grade A",
            "code": "GRA",
            "hourly_rate": 35.0,
        })
        cls.post_type = cls.env["security.post.type"].create({
            "name": "Main Post Type",
            "code": "MPT",
            "min_grade_id": cls.grade_a.id,
        })
        cls.site = cls.env["security.client.site"].create({
            "name": "Adcon Brakwater Site 037",
            "partner_id": cls.partner.id,
        })
        cls.post = cls.env["security.post"].create({
            "name": "Main Post",
            "site_id": cls.site.id,
            "post_type_id": cls.post_type.id,
            "partner_id": cls.partner.id,
        })
        cls.guard_1 = cls.env["hr.employee"].create({
            "name": "Guard Johannes",
            "security_guard": True,
            "security_grade_id": cls.grade_a.id,
        })
        cls.guard_2 = cls.env["hr.employee"].create({
            "name": "Guard Wilbert",
            "security_guard": True,
            "security_grade_id": cls.grade_a.id,
        })

    def test_01_shift_requirement_increase_guard_count_auto_spawns_slots(self):
        """Increasing guard_count from 1 to 2 auto-spawns slot 2 for remainder of cycle."""
        today = date.today()
        cycle_from, cycle_to = self.env["security.roster.batch"].get_operational_cycle_dates(today)

        batch = self.env["security.roster.batch"].create({
            "site_id": self.site.id,
            "date_from": cycle_from,
            "date_to": cycle_to,
        })

        req = self.env["security.shift.requirement"].create({
            "site_id": self.site.id,
            "post_id": self.post.id,
            "shift_template_id": self.shift_day.id,
            "guard_count": 1,
        })

        batch.action_generate_slots()

        # Slot 1 should exist for today
        slot_1 = self.env["security.roster.slot"].search([
            ("site_id", "=", self.site.id),
            ("shift_date", "=", today),
            ("shift_requirement_id", "=", req.id),
            ("slot_number", "=", 1),
            ("state", "!=", "cancelled"),
        ])
        self.assertTrue(slot_1, "Slot 1 must exist after generation")

        # Slot 2 should not exist yet
        slot_2_before = self.env["security.roster.slot"].search([
            ("site_id", "=", self.site.id),
            ("shift_date", "=", today),
            ("shift_requirement_id", "=", req.id),
            ("slot_number", "=", 2),
            ("state", "!=", "cancelled"),
        ])
        self.assertFalse(slot_2_before, "Slot 2 should not exist before count increase")

        # Now update guard_count to 2
        req.write({"guard_count": 2})

        # Slot 2 should now automatically exist!
        slot_2_after = self.env["security.roster.slot"].search([
            ("site_id", "=", self.site.id),
            ("shift_date", "=", today),
            ("shift_requirement_id", "=", req.id),
            ("slot_number", "=", 2),
            ("state", "!=", "cancelled"),
        ])
        self.assertTrue(slot_2_after, "Slot 2 must be auto-spawned when guard_count increased to 2")

    def test_02_shift_requirement_decrease_guard_count_auto_cancels_excess_slots(self):
        """Decreasing guard_count from 2 to 1 cancels unassigned future slots with slot_number=2."""
        today = date.today()
        cycle_from, cycle_to = self.env["security.roster.batch"].get_operational_cycle_dates(today)

        batch = self.env["security.roster.batch"].create({
            "site_id": self.site.id,
            "date_from": cycle_from,
            "date_to": cycle_to,
        })

        req = self.env["security.shift.requirement"].create({
            "site_id": self.site.id,
            "post_id": self.post.id,
            "shift_template_id": self.shift_day.id,
            "guard_count": 2,
        })

        batch.action_generate_slots()

        slot_2 = self.env["security.roster.slot"].search([
            ("site_id", "=", self.site.id),
            ("shift_date", "=", today),
            ("shift_requirement_id", "=", req.id),
            ("slot_number", "=", 2),
            ("state", "!=", "cancelled"),
        ])
        self.assertTrue(slot_2, "Slot 2 exists before decrease")

        # Reduce guard_count back to 1
        req.write({"guard_count": 1})

        slot_2_after = self.env["security.roster.slot"].search([
            ("site_id", "=", self.site.id),
            ("shift_date", "=", today),
            ("shift_requirement_id", "=", req.id),
            ("slot_number", "=", 2),
            ("state", "!=", "cancelled"),
        ])
        self.assertFalse(slot_2_after, "Slot 2 must be cancelled when requirement decreased to 1")

        cancelled_slot = self.env["security.roster.slot"].search([
            ("site_id", "=", self.site.id),
            ("shift_date", "=", today),
            ("shift_requirement_id", "=", req.id),
            ("slot_number", "=", 2),
            ("state", "=", "cancelled"),
        ])
        self.assertTrue(cancelled_slot, "Cancelled slot record is preserved in cancelled state")
        self.assertFalse(cancelled_slot.critical_gap, "Cancelled slot must not flag critical gap")

    def test_03_contract_shift_requirement_sync(self):
        """Changing guard_count on contract shift requirement updates linked requirement."""
        contract = self.env["security.client.contract"].create({
            "name": "Adcon Mining Master Contract",
            "partner_id": self.partner.id,
            "date_start": date.today() - timedelta(days=30),
            "state": "active",
        })
        c_site = self.env["security.contract.site"].create({
            "contract_id": contract.id,
            "name": "Brakwater Post",
            "site_id": self.site.id,
        })
        c_post = self.env["security.contract.post"].create({
            "contract_site_id": c_site.id,
            "name": "Main Post",
        })
        req = self.env["security.shift.requirement"].create({
            "site_id": self.site.id,
            "post_id": self.post.id,
            "shift_template_id": self.shift_night.id,
            "guard_count": 1,
        })
        c_req = self.env["security.contract.shift.requirement"].create({
            "contract_site_id": c_site.id,
            "contract_post_id": c_post.id,
            "shift_template_id": self.shift_night.id,
            "guard_count": 1,
            "requirement_id": req.id,
        })

        # Update guard count on contract side
        c_req.write({"guard_count": 2})
        self.assertEqual(req.guard_count, 2, "Operational requirement must sync guard_count from contract")

    def test_04_slot_unassign_action(self):
        """action_unassign clears guard, resets state to draft, and clears flags."""
        slot = self.env["security.roster.slot"].create({
            "site_id": self.site.id,
            "post_id": self.post.id,
            "shift_template_id": self.shift_day.id,
            "shift_date": date.today(),
            "slot_number": 1,
            "employee_id": self.guard_1.id,
            "state": "assigned",
            "is_relief": True,
            "relief_reason": "Testing relief",
            "is_override": True,
            "override_reason": "Approved",
        })

        slot.action_unassign()
        self.assertFalse(slot.employee_id)
        self.assertEqual(slot.state, "draft")
        self.assertFalse(slot.is_relief)
        self.assertFalse(slot.is_override)
        self.assertFalse(slot.critical_gap)

    def test_05_slot_cancel_and_reset_draft(self):
        """action_cancel_slot cancels slot and action_reset_draft re-opens it."""
        slot = self.env["security.roster.slot"].create({
            "site_id": self.site.id,
            "post_id": self.post.id,
            "shift_template_id": self.shift_day.id,
            "shift_date": date.today(),
            "slot_number": 1,
            "state": "draft",
        })

        slot.action_cancel_slot()
        self.assertEqual(slot.state, "cancelled")
        self.assertFalse(slot.critical_gap)
        self.assertEqual(slot.readiness_state, "ready")

        slot.action_reset_draft()
        self.assertEqual(slot.state, "draft")
        self.assertFalse(slot.critical_gap)

    def test_06_adhoc_slot_creation(self):
        """action_create_adhoc_slot creates an ad-hoc slot for a specific date and site."""
        res = self.env["security.roster.slot"].action_create_adhoc_slot(
            site_id=self.site.id,
            shift_date=str(date.today()),
            shift_template_id=self.shift_day.id,
            post_id=self.post.id,
        )
        self.assertTrue(res.get("id"))
        slot = self.env["security.roster.slot"].browse(res["id"])
        self.assertEqual(slot.site_id.id, self.site.id)
        self.assertEqual(slot.post_id.id, self.post.id)
        self.assertEqual(slot.shift_template_id.id, self.shift_day.id)
        self.assertEqual(slot.state, "draft")

    def test_07_contract_action_sync_current_cycle_slots(self):
        """action_sync_current_cycle_slots on contract triggers site sync."""
        contract = self.env["security.client.contract"].create({
            "name": "Adcon Contract for Sync Test",
            "partner_id": self.partner.id,
            "date_start": date.today() - timedelta(days=10),
            "state": "active",
        })
        self.env["security.contract.site"].create({
            "contract_id": contract.id,
            "name": "Brakwater Post",
            "site_id": self.site.id,
        })
        self.env["security.shift.requirement"].create({
            "site_id": self.site.id,
            "post_id": self.post.id,
            "shift_template_id": self.shift_day.id,
            "guard_count": 1,
        })

        res = contract.action_sync_current_cycle_slots()
        self.assertEqual(res.get("type"), "ir.actions.client")
        self.assertEqual(res.get("params", {}).get("type"), "success")
