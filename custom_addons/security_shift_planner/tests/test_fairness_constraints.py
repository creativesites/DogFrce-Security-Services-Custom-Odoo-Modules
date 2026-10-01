from datetime import date, timedelta
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestFairnessConstraints(TransactionCase):
    """
    Test suite for deterministic hard fairness constraints:
    - Max 1 Sunday per guard per 21st-20th cycle
    - Max working days limit (default 22 days per cycle)
    - Minimum rest interval (12h between night and day shifts)
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env

        cls.partner = env["res.partner"].create({"name": "Fairness Client", "is_company": True})
        cls.site = env["security.client.site"].create({"name": "Fairness Site", "partner_id": cls.partner.id})

        cls.post_type = env["security.post.type"].create({"name": "Guard Post"})
        cls.post = env["security.post"].with_context(allow_standalone_post=True).create({
            "name": "Gate 1",
            "site_id": cls.site.id,
            "post_type_id": cls.post_type.id,
        })

        cls.shift_day = env["security.shift.template"].create({
            "name": "Day 06-18",
            "start_hour": 6.0,
            "end_hour": 18.0,
            "shift_category": "day",
            "duration_hours": 12.0,
        })
        cls.shift_night = env["security.shift.template"].create({
            "name": "Night 18-06",
            "start_hour": 18.0,
            "end_hour": 6.0,
            "shift_category": "night",
            "duration_hours": 12.0,
        })

        # Operational cycle: 2026-02-21 to 2026-03-20
        cls.batch = env["security.roster.batch"].create({
            "partner_id": cls.partner.id,
            "date_from": "2026-02-21",
            "date_to": "2026-03-20",
            "site_ids": [(4, cls.site.id)],
        })

        cls.guard = env["hr.employee"].create({
            "name": "Guard Johannes",
            "security_guard": True,
            "active": True,
            "security_disqualified": False,
        })

    def test_max_one_sunday_per_cycle_constraint(self):
        """A guard must not be scheduled for more than 1 Sunday in the same 21st-to-20th cycle."""
        # Sundays in cycle 2026-02-21 to 2026-03-20:
        # 2026-02-22 (Sunday), 2026-03-01 (Sunday), 2026-03-08 (Sunday), 2026-03-15 (Sunday)
        sun1_date = "2026-02-22"
        sun2_date = "2026-03-01"

        slot1 = self.env["security.roster.slot"].create({
            "batch_id": self.batch.id,
            "post_id": self.post.id,
            "site_id": self.site.id,
            "shift_date": sun1_date,
            "shift_template_id": self.shift_day.id,
            "employee_id": self.guard.id,
            "state": "confirmed",
        })

        slot2 = self.env["security.roster.slot"].create({
            "batch_id": self.batch.id,
            "post_id": self.post.id,
            "site_id": self.site.id,
            "shift_date": sun2_date,
            "shift_template_id": self.shift_day.id,
            "state": "draft",
        })

        eligible, reason = slot2.check_guard_eligibility(self.guard)
        self.assertFalse(eligible, "Guard must be ineligible for a 2nd Sunday in the same cycle")
        self.assertIn("Sunday", reason)

    def test_max_working_days_per_cycle_constraint(self):
        """A guard must not exceed max working days (default 22) in the same cycle."""
        self.env["ir.config_parameter"].sudo().set_param(
            "security_roster.max_working_days_per_cycle", "22"
        )

        # Create 22 working day slots starting from 2026-02-21
        start_d = date(2026, 2, 21)
        created_slots = []
        for i in range(22):
            cur_date = start_d + timedelta(days=i)
            # Skip Sundays to isolate working days constraint
            if cur_date.weekday() == 6:
                cur_date += timedelta(days=1)
            slot = self.env["security.roster.slot"].create({
                "batch_id": self.batch.id,
                "post_id": self.post.id,
                "site_id": self.site.id,
                "shift_date": cur_date.strftime("%Y-%m-%d"),
                "shift_template_id": self.shift_day.id,
                "employee_id": self.guard.id,
                "state": "confirmed",
            })
            created_slots.append(slot)

        # Attempt 23rd day slot
        slot_23 = self.env["security.roster.slot"].create({
            "batch_id": self.batch.id,
            "post_id": self.post.id,
            "site_id": self.site.id,
            "shift_date": "2026-03-18",
            "shift_template_id": self.shift_day.id,
            "state": "draft",
        })

        eligible, reason = slot_23.check_guard_eligibility(self.guard)
        self.assertFalse(eligible, "Guard must be ineligible after reaching max working days")
        self.assertIn("working days", reason.lower())

    def test_minimum_rest_interval_day_night(self):
        """Guard working night shift must have required rest interval before day shift."""
        # Night shift on 2026-02-23 (18:00 - 06:00 next morning)
        night_slot = self.env["security.roster.slot"].create({
            "batch_id": self.batch.id,
            "post_id": self.post.id,
            "site_id": self.site.id,
            "shift_date": "2026-02-23",
            "shift_template_id": self.shift_night.id,
            "employee_id": self.guard.id,
            "state": "confirmed",
        })

        # Day shift on 2026-02-24 (06:00 - 18:00) -> 0 hours rest
        day_slot = self.env["security.roster.slot"].create({
            "batch_id": self.batch.id,
            "post_id": self.post.id,
            "site_id": self.site.id,
            "shift_date": "2026-02-24",
            "shift_template_id": self.shift_day.id,
            "state": "draft",
        })

        eligible, reason = day_slot.check_guard_eligibility(self.guard)
        self.assertFalse(eligible, "Guard cannot work morning shift immediately following night shift")
        self.assertIn("rest", reason.lower())
