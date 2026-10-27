# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestShiftSwap(TransactionCase):
    """
    Test suite authored by Lead Independent Verifier (@Kael 🛡️)
    Verifying Shift Swap Engine in DogForce Security Services:
    a) Clean atomic swapping of two assigned guards between slots.
    b) Rejection/blocking of a swap if it would violate the 12-hour turnaround rest rule.
    c) Rejection if a guard's grade does not meet the post's minimum grade.
    d) Manager audit reason requirement & override lifecycle.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env

        # Client and Sites
        cls.client = env["res.partner"].create({
            "name": "Namibia Diamond Trading (NDTC) Test",
            "is_company": True,
        })
        cls.site = env["security.client.site"].create({
            "name": "NDTC Head Office Site",
            "partner_id": cls.client.id,
            "guard_pool_mode": "site_then_relief",
        })

        # Grades (Grade A: seq 1, Grade B: seq 2, Grade C: seq 3)
        cls.grade_a = env["security.grade"].create({
            "name": "Grade A Premium",
            "code": "SWAP_GRA",
            "sequence": 1,
            "hourly_rate": 35.0,
        })
        cls.grade_b = env["security.grade"].create({
            "name": "Grade B Standard",
            "code": "SWAP_GRB",
            "sequence": 2,
            "hourly_rate": 28.0,
        })
        cls.grade_c = env["security.grade"].create({
            "name": "Grade C Basic",
            "code": "SWAP_GRC",
            "sequence": 3,
            "hourly_rate": 22.0,
        })

        # Post Types
        cls.post_type_vault = env["security.post.type"].create({
            "name": "Diamond Vault Security",
            "code": "DVS01",
            "min_grade_id": cls.grade_a.id,
        })
        cls.post_type_gate = env["security.post.type"].create({
            "name": "Perimeter Gate",
            "code": "PG01",
            "min_grade_id": cls.grade_c.id,
        })

        # Posts
        cls.post_vault = env["security.post"].with_context(allow_standalone_post=True).create({
            "name": "Main Vault Control Room",
            "site_id": cls.site.id,
            "post_type_id": cls.post_type_vault.id,
        })
        cls.post_gate = env["security.post"].with_context(allow_standalone_post=True).create({
            "name": "South Vehicle Boom Gate",
            "site_id": cls.site.id,
            "post_type_id": cls.post_type_gate.id,
        })

        # Shift Templates
        cls.shift_day = env["security.shift.template"].create({
            "name": "Day Shift 12h (06:00 - 18:00)",
            "start_hour": 6.0,
            "end_hour": 18.0,
            "duration_hours": 12.0,
        })
        cls.shift_night = env["security.shift.template"].create({
            "name": "Night Shift 12h (18:00 - 06:00)",
            "start_hour": 18.0,
            "end_hour": 6.0,
            "duration_hours": 12.0,
        })

        # Guards
        cls.guard_alpha = env["hr.employee"].create({
            "name": "Kavango Shikongo",
            "employee_code": "DF-SWAP-01",
            "security_guard": True,
            "security_grade_id": cls.grade_a.id,
            "active": True,
            "security_disqualified": False,
        })
        cls.guard_beta = env["hr.employee"].create({
            "name": "Johannes Amukoto",
            "employee_code": "DF-SWAP-02",
            "security_guard": True,
            "security_grade_id": cls.grade_a.id,
            "active": True,
            "security_disqualified": False,
        })
        cls.guard_charlie = env["hr.employee"].create({
            "name": "Petrus Shilongo",
            "employee_code": "DF-SWAP-03",
            "security_guard": True,
            "security_grade_id": cls.grade_c.id,
            "active": True,
            "security_disqualified": False,
        })

        # Enroll all in site pool
        cls.site.write({
            "site_guard_pool_ids": [
                (4, cls.guard_alpha.id),
                (4, cls.guard_beta.id),
                (4, cls.guard_charlie.id),
            ]
        })

        # Operational batch
        cls.batch = env["security.roster.batch"].create({
            "name": "Cycle Nov 2026 Test",
            "partner_id": cls.client.id,
            "site_id": cls.site.id,
            "date_from": date(2026, 11, 1),
            "date_to": date(2026, 11, 30),
            "state": "generated",
        })

    def test_01_clean_atomic_swap_between_guards(self):
        """Verify clean atomic swapping of two assigned guards between slots without compliance issues."""
        slot1 = self.env["security.roster.slot"].create({
            "batch_id": self.batch.id,
            "site_id": self.site.id,
            "post_id": self.post_gate.id,
            "shift_template_id": self.shift_day.id,
            "shift_date": date(2026, 11, 2),
            "employee_id": self.guard_alpha.id,
            "state": "assigned",
        })
        slot2 = self.env["security.roster.slot"].create({
            "batch_id": self.batch.id,
            "site_id": self.site.id,
            "post_id": self.post_gate.id,
            "shift_template_id": self.shift_day.id,
            "shift_date": date(2026, 11, 3),
            "employee_id": self.guard_beta.id,
            "state": "assigned",
        })

        # 1. Validate swap payload
        val = slot1.action_validate_swap(slot2.id)
        self.assertEqual(val["status"], "success")
        self.assertTrue(val["can_swap_cleanly"])
        self.assertFalse(val["requires_override"])
        self.assertFalse(val["is_hard_blocked"])

        # 2. Execute swap
        result = slot1.action_swap_guards(slot2.id, reason="Guard mutual shift swap request")
        self.assertEqual(result["status"], "success")

        # 3. Verify database state
        slot1.invalidate_recordset()
        slot2.invalidate_recordset()
        self.assertEqual(slot1.employee_id.id, self.guard_beta.id, "Slot 1 should now be assigned to Guard Beta")
        self.assertEqual(slot2.employee_id.id, self.guard_alpha.id, "Slot 2 should now be assigned to Guard Alpha")
        self.assertFalse(slot1.is_override, "Clean swap should not be flagged as an override")
        self.assertFalse(slot2.is_override, "Clean swap should not be flagged as an override")

        # 4. Verify convenience wrapper swap_with_slot swaps them back
        res_back = slot1.action_swap_with_slot(slot2, reason="Swapping guards back to initial posts")
        self.assertEqual(res_back["status"], "success")
        slot1.invalidate_recordset()
        slot2.invalidate_recordset()
        self.assertEqual(slot1.employee_id.id, self.guard_alpha.id)
        self.assertEqual(slot2.employee_id.id, self.guard_beta.id)

    def test_02_rejection_blocking_12h_turnaround_rest_violation(self):
        """Verify rejection/blocking of a swap if it would violate the 12-hour turnaround rest rule."""
        # Guard Alpha works overnight night shift on 2026-11-04 (18:00 to 06:00 on 2026-11-05)
        night_shift = self.env["security.roster.slot"].create({
            "batch_id": self.batch.id,
            "site_id": self.site.id,
            "post_id": self.post_gate.id,
            "shift_template_id": self.shift_night.id,
            "shift_date": date(2026, 11, 4),
            "employee_id": self.guard_alpha.id,
            "state": "assigned",
        })

        # Slot A: 2026-11-07 Day shift (well clear of night shift), assigned to Guard Alpha
        slot_a = self.env["security.roster.slot"].create({
            "batch_id": self.batch.id,
            "site_id": self.site.id,
            "post_id": self.post_gate.id,
            "shift_template_id": self.shift_day.id,
            "shift_date": date(2026, 11, 7),
            "employee_id": self.guard_alpha.id,
            "state": "assigned",
        })

        # Slot B: 2026-11-05 Morning Day shift (06:00 - 18:00), assigned to Guard Beta
        # If Guard Alpha swaps into Slot B, Guard Alpha finishes night shift at 06:00 and immediately starts Day shift at 06:00 (0 hours rest!)
        slot_b = self.env["security.roster.slot"].create({
            "batch_id": self.batch.id,
            "site_id": self.site.id,
            "post_id": self.post_gate.id,
            "shift_template_id": self.shift_day.id,
            "shift_date": date(2026, 11, 5),
            "employee_id": self.guard_beta.id,
            "state": "assigned",
        })

        # 1. Validation must catch turnaround rest breach
        val = slot_a.action_validate_swap(slot_b.id)
        self.assertEqual(val["status"], "success")
        self.assertFalse(val["can_swap_cleanly"])
        self.assertTrue(val["requires_override"])
        self.assertFalse(val["guard_a"]["rest_ok"], "Guard Alpha must fail turnaround rest check")
        self.assertIn("rest", val["guard_a"]["rest_reason"].lower())

        # 2. Swap attempt without override must be blocked
        res_blocked = slot_a.action_swap_guards(slot_b.id, reason="Attempted swap", allow_override=False)
        self.assertEqual(res_blocked["status"], "override_required")
        self.assertTrue(any("rest" in w.lower() for w in res_blocked.get("warnings", [])))

        # 3. Verify database state is untouched (atomic protection)
        slot_a.invalidate_recordset()
        slot_b.invalidate_recordset()
        self.assertEqual(slot_a.employee_id.id, self.guard_alpha.id)
        self.assertEqual(slot_b.employee_id.id, self.guard_beta.id)

        # 4. action_swap_with_slot with raise_on_error=True raises UserError
        with self.assertRaises(UserError):
            slot_a.action_swap_with_slot(slot_b, raise_on_error=True)

    def test_03_rejection_guard_grade_does_not_meet_post_minimum_grade(self):
        """Verify rejection/blocking if a guard's grade does not meet the post's minimum grade."""
        # Slot Vault: requires Grade A (Main Vault Control Room)
        slot_vault = self.env["security.roster.slot"].create({
            "batch_id": self.batch.id,
            "site_id": self.site.id,
            "post_id": self.post_vault.id,
            "shift_template_id": self.shift_day.id,
            "shift_date": date(2026, 11, 10),
            "employee_id": self.guard_alpha.id,  # Grade A
            "state": "assigned",
        })

        # Slot Gate: requires Grade C (South Vehicle Boom Gate)
        slot_gate = self.env["security.roster.slot"].create({
            "batch_id": self.batch.id,
            "site_id": self.site.id,
            "post_id": self.post_gate.id,
            "shift_template_id": self.shift_day.id,
            "shift_date": date(2026, 11, 10),
            "employee_id": self.guard_charlie.id,  # Grade C
            "state": "assigned",
        })

        # 1. Validation must flag Guard Charlie lacks minimum Grade A for Vault post
        val = slot_vault.action_validate_swap(slot_gate.id)
        self.assertEqual(val["status"], "success")
        self.assertFalse(val["can_swap_cleanly"])
        self.assertTrue(val["requires_override"])
        self.assertFalse(val["guard_b"]["grade_ok"], "Guard Charlie (Grade C) cannot cleanly take Vault post")
        self.assertIn("grade", val["guard_b"]["grade_message"].lower())

        # 2. Swap without override must return override_required
        res_blocked = slot_vault.action_swap_guards(slot_gate.id, reason="Swap guards", allow_override=False)
        self.assertEqual(res_blocked["status"], "override_required")
        self.assertTrue(any("grade" in w.lower() for w in res_blocked.get("warnings", [])))

        # 3. Database records remain untouched
        slot_vault.invalidate_recordset()
        slot_gate.invalidate_recordset()
        self.assertEqual(slot_vault.employee_id.id, self.guard_alpha.id)
        self.assertEqual(slot_gate.employee_id.id, self.guard_charlie.id)

        # 4. Manager override flow with valid justification
        res_override = slot_vault.action_swap_guards(
            slot_gate.id,
            reason="Operations Manager Wilbert emergency override: Guard Charlie supervised under senior officer",
            allow_override=True,
        )
        self.assertEqual(res_override["status"], "success")

        slot_vault.invalidate_recordset()
        slot_gate.invalidate_recordset()
        self.assertEqual(slot_vault.employee_id.id, self.guard_charlie.id)
        self.assertEqual(slot_gate.employee_id.id, self.guard_alpha.id)
        self.assertTrue(slot_vault.is_override)
        self.assertIn("emergency override", slot_vault.override_reason)

    def test_04_swap_requires_manager_audit_reason(self):
        """Verify that any swap attempt without an audit reason is strictly rejected."""
        slot1 = self.env["security.roster.slot"].create({
            "batch_id": self.batch.id,
            "site_id": self.site.id,
            "post_id": self.post_gate.id,
            "shift_template_id": self.shift_day.id,
            "shift_date": date(2026, 11, 12),
            "employee_id": self.guard_alpha.id,
            "state": "assigned",
        })
        slot2 = self.env["security.roster.slot"].create({
            "batch_id": self.batch.id,
            "site_id": self.site.id,
            "post_id": self.post_gate.id,
            "shift_template_id": self.shift_day.id,
            "shift_date": date(2026, 11, 13),
            "employee_id": self.guard_beta.id,
            "state": "assigned",
        })

        # Blank reason
        res_blank = slot1.action_swap_guards(slot2.id, reason="   ")
        self.assertEqual(res_blank["status"], "error")
        self.assertIn("reason", res_blank["message"].lower())
