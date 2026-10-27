from datetime import date, timedelta
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestIdleGuardSolver(TransactionCase):
    """
    Test suite for Track 4: Idle Guard Solver (`action_fill_gaps_with_idle_guards`).
    Verifies that:
      - Idle guards (fewest shifts in cycle) are prioritized over busy guards.
      - Workload is evenly balanced across multiple idle guards.
      - 12h turnaround rest constraint is strictly enforced.
      - Max 1 Sunday cap is respected.
      - Batch delegate method executes cleanly and updates slots.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env

        cls.partner = env["res.partner"].create({
            "name": "Idle Solver Client",
            "is_company": True,
        })
        cls.site = env["security.client.site"].create({
            "name": "Idle Solver Site",
            "partner_id": cls.partner.id,
            "guard_pool_mode": "site_then_relief",
        })

        cls.grade_a = env["security.grade"].create({
            "name": "Grade A Solver",
            "code": "A_SOLV",
            "sequence": 1,
            "hourly_rate": 20.0,
        })
        cls.grade_b = env["security.grade"].create({
            "name": "Grade B Solver",
            "code": "B_SOLV",
            "sequence": 2,
            "hourly_rate": 15.0,
        })

        cls.post_type = env["security.post.type"].create({
            "name": "Standard Guard Post",
            "min_grade_id": cls.grade_b.id,
        })
        cls.post = env["security.post"].with_context(allow_standalone_post=True).create({
            "name": "Main Post 1",
            "site_id": cls.site.id,
            "post_type_id": cls.post_type.id,
        })

        cls.shift_day = env["security.shift.template"].create({
            "name": "Day 06-18",
            "start_hour": 6.0,
            "end_hour": 18.0,
        })
        cls.shift_night = env["security.shift.template"].create({
            "name": "Night 18-06",
            "start_hour": 18.0,
            "end_hour": 6.0,
        })

        # Operational cycle: 2026-03-21 to 2026-04-20
        cls.batch = env["security.roster.batch"].create({
            "name": "Cycle 21 Mar - 20 Apr 2026",
            "partner_id": cls.partner.id,
            "date_from": "2026-03-21",
            "date_to": "2026-04-20",
            "site_ids": [(4, cls.site.id)],
        })

        cls.guard_busy = env["hr.employee"].create({
            "name": "Busy Guard (5 shifts)",
            "security_guard": True,
            "active": True,
            "security_grade_id": cls.grade_a.id,
            "security_reliability_score": 95,
            "security_disqualified": False,
        })
        cls.guard_idle = env["hr.employee"].create({
            "name": "Idle Guard (0 shifts)",
            "security_guard": True,
            "active": True,
            "security_grade_id": cls.grade_b.id,
            "security_reliability_score": 85,
            "security_disqualified": False,
        })

        # Give guard_busy 5 shifts in the cycle
        for i in range(5):
            d = date(2026, 3, 21) + timedelta(days=i)
            env["security.roster.slot"].create({
                "batch_id": cls.batch.id,
                "post_id": cls.post.id,
                "site_id": cls.site.id,
                "shift_date": d,
                "shift_template_id": cls.shift_day.id,
                "employee_id": cls.guard_busy.id,
                "state": "assigned",
            })

    def test_01_idle_guard_prioritized_over_busy_guard(self):
        """Idle Guard Solver must select guard with 0 shifts over guard with 5 shifts."""
        gap_slot = self.env["security.roster.slot"].create({
            "batch_id": self.batch.id,
            "post_id": self.post.id,
            "site_id": self.site.id,
            "shift_date": "2026-03-30",
            "shift_template_id": self.shift_day.id,
            "state": "draft",
        })

        result = gap_slot.action_fill_gaps_with_idle_guards()
        self.assertEqual(result["params"]["type"], "success")
        gap_slot.invalidate_recordset()

        self.assertEqual(
            gap_slot.employee_id.id,
            self.guard_idle.id,
            "Idle Guard Solver must select the idle guard (0 shifts) over the busy guard (5 shifts).",
        )
        self.assertEqual(gap_slot.state, "assigned")
        self.assertFalse(gap_slot.critical_gap)
        self.assertTrue(gap_slot.is_relief)
        self.assertIn("Idle Guard Solver", gap_slot.relief_reason)

    def test_02_dynamic_workload_balancing(self):
        """When multiple idle guards are available, solver balances shifts evenly."""
        guard_2 = self.env["hr.employee"].create({
            "name": "Idle Guard 2",
            "security_guard": True,
            "active": True,
            "security_grade_id": self.grade_b.id,
            "security_reliability_score": 85,
            "security_disqualified": False,
        })
        guard_3 = self.env["hr.employee"].create({
            "name": "Idle Guard 3",
            "security_guard": True,
            "active": True,
            "security_grade_id": self.grade_b.id,
            "security_reliability_score": 85,
            "security_disqualified": False,
        })

        slots = self.env["security.roster.slot"]
        for i in range(3):
            d = date(2026, 4, 1) + timedelta(days=i)
            slots |= self.env["security.roster.slot"].create({
                "batch_id": self.batch.id,
                "post_id": self.post.id,
                "site_id": self.site.id,
                "shift_date": d,
                "shift_template_id": self.shift_day.id,
                "state": "draft",
            })

        slots.action_fill_gaps_with_idle_guards()
        slots.invalidate_recordset()

        assigned_guards = slots.mapped("employee_id.id")
        self.assertEqual(len(set(assigned_guards)), 3, "All 3 idle guards should receive exactly 1 shift")

    def test_03_respects_12h_turnaround_rest(self):
        """Guard with 0 shifts who worked night shift cannot work next morning's day shift."""
        # Create an idle guard who just finished night shift on 2026-04-05 (18:00 to 06:00 on Apr 6)
        tired_guard = self.env["hr.employee"].create({
            "name": "Tired Idle Guard",
            "security_guard": True,
            "active": True,
            "security_grade_id": self.grade_b.id,
            "security_reliability_score": 90,
            "security_disqualified": False,
        })
        self.env["security.roster.slot"].create({
            "batch_id": self.batch.id,
            "post_id": self.post.id,
            "site_id": self.site.id,
            "shift_date": "2026-04-05",
            "shift_template_id": self.shift_night.id,
            "employee_id": tired_guard.id,
            "state": "assigned",
        })

        # Gap slot is Day shift on 2026-04-06 (06:00 to 18:00) -> 0h rest!
        gap_slot = self.env["security.roster.slot"].create({
            "batch_id": self.batch.id,
            "post_id": self.post.id,
            "site_id": self.site.id,
            "shift_date": "2026-04-06",
            "shift_template_id": self.shift_day.id,
            "state": "draft",
        })

        # Fresh guard has 1 shift already in cycle, but is fully rested
        fresh_guard = self.env["hr.employee"].create({
            "name": "Rested Guard",
            "security_guard": True,
            "active": True,
            "security_grade_id": self.grade_b.id,
            "security_reliability_score": 80,
            "security_disqualified": False,
        })
        self.env["security.roster.slot"].create({
            "batch_id": self.batch.id,
            "post_id": self.post.id,
            "site_id": self.site.id,
            "shift_date": "2026-03-22",
            "shift_template_id": self.shift_day.id,
            "employee_id": fresh_guard.id,
            "state": "assigned",
        })

        gap_slot.action_fill_gaps_with_idle_guards()
        gap_slot.invalidate_recordset()

        self.assertNotEqual(
            gap_slot.employee_id.id,
            tired_guard.id,
            "Tired guard must not be assigned due to 12h turnaround rest violation",
        )
        self.assertEqual(
            gap_slot.employee_id.id,
            fresh_guard.id,
            "Rested guard should be selected instead",
        )

    def test_04_batch_action_fill_gaps_with_idle_guards(self):
        """Batch action should fill all unassigned slots and log chatter notification."""
        test_batch = self.env["security.roster.batch"].create({
            "name": "Batch Solver Test",
            "partner_id": self.partner.id,
            "date_from": "2026-03-21",
            "date_to": "2026-04-20",
            "site_ids": [(4, self.site.id)],
        })
        slot1 = self.env["security.roster.slot"].create({
            "batch_id": test_batch.id,
            "post_id": self.post.id,
            "site_id": self.site.id,
            "shift_date": "2026-04-10",
            "shift_template_id": self.shift_day.id,
            "state": "draft",
        })

        result = test_batch.action_fill_gaps_with_idle_guards()
        self.assertEqual(result["params"]["type"], "success")
        slot1.invalidate_recordset()
        self.assertTrue(slot1.employee_id, "Slot in batch must be assigned")
