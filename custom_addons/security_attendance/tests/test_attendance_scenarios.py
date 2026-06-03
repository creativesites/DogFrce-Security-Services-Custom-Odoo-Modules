"""
Integration tests for security.attendance.record computed fields.

Each test creates the minimal roster infrastructure (partner, site, post,
shift template, slot) and an attendance record, then verifies that the
computed attendance metrics and shift-bucket fields are correct.

Coverage:
  1. Present guard — worked_hours computed from check-in/out
  2. AWOL guard — worked_hours == 0, no_work_no_pay == True
  3. Late arrival — late_minutes computed correctly
  4. Night shift (18:00–06:00) — night_hours > 0
  5. Sunday shift — sunday_hours > 0
"""

from datetime import date

from odoo.tests.common import TransactionCase


class TestAttendanceScenarios(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Minimal client / site / post / shift-template infrastructure
        cls.partner = cls.env["res.partner"].create({"name": "Attendance Scenario Client"})
        cls.site = cls.env["security.client.site"].create({
            "name": "Scenario Site",
            "partner_id": cls.partner.id,
        })
        cls.post_type = cls.env["security.post.type"].create({"name": "Scenario Post Type"})
        cls.post = cls.env["security.post"].create({
            "name": "Scenario Post",
            "partner_id": cls.partner.id,
            "site_id": cls.site.id,
            "post_type_id": cls.post_type.id,
        })
        cls.guard = cls.env["hr.employee"].create({
            "name": "Scenario Guard",
            "security_guard": True,
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _day_shift_slot(self, date_str, start_hour=6.0, end_hour=14.0):
        """Create a shift template and roster slot for the given date."""
        template = self.env["security.shift.template"].create({
            "name": "Day Shift %s-%s" % (start_hour, end_hour),
            "start_hour": start_hour,
            "end_hour": end_hour,
        })
        slot = self.env["security.roster.slot"].create({
            "shift_date": date_str,
            "post_id": self.post.id,
            "shift_template_id": template.id,
            "employee_id": self.guard.id,
        })
        return slot

    def _night_shift_slot(self, date_str):
        """Create a slot for an 18:00–06:00 night shift (end hour next day)."""
        template = self.env["security.shift.template"].create({
            "name": "Night Shift 18-06",
            "start_hour": 18.0,
            "end_hour": 6.0,   # model handles next-day rollover (end <= start → +1 day)
        })
        slot = self.env["security.roster.slot"].create({
            "shift_date": date_str,
            "post_id": self.post.id,
            "shift_template_id": template.id,
            "employee_id": self.guard.id,
        })
        return slot

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_present_guard_computes_hours(self):
        """Check-in 06:00, check-out 14:00 → worked_hours == 8.0, status == 'present'."""
        slot = self._day_shift_slot("2026-05-04", start_hour=6.0, end_hour=14.0)
        rec = self.env["security.attendance.record"].create({
            "roster_slot_id": slot.id,
            "check_in": "2026-05-04 06:00:00",
            "check_out": "2026-05-04 14:00:00",
        })
        self.assertAlmostEqual(rec.worked_hours, 8.0, places=2,
                               msg="worked_hours must equal check-out minus check-in.")
        self.assertEqual(rec.status, "present",
                         msg="Status should be 'present' for on-time full-shift attendance.")
        self.assertAlmostEqual(rec.valid_hours, 8.0, places=2)

    def test_awol_guard_zero_hours(self):
        """AWOL record → worked_hours == 0, no_work_no_pay True, status == 'absent'."""
        slot = self._day_shift_slot("2026-05-05", start_hour=6.0, end_hour=14.0)
        rec = self.env["security.attendance.record"].create({
            "roster_slot_id": slot.id,
            "manual_presence": "awol",
            "absence_type": "awol",
        })
        self.assertEqual(rec.worked_hours, 0.0,
                         msg="AWOL guard must have zero worked hours.")
        self.assertTrue(rec.no_work_no_pay,
                        msg="AWOL record must be flagged no_work_no_pay.")
        self.assertEqual(rec.status, "absent",
                         msg="AWOL status must resolve to 'absent'.")

    def test_late_minutes_computed(self):
        """Check-in 15 minutes after scheduled start (06:00) → late_minutes == 15."""
        slot = self._day_shift_slot("2026-05-06", start_hour=6.0, end_hour=14.0)
        rec = self.env["security.attendance.record"].create({
            "roster_slot_id": slot.id,
            "check_in": "2026-05-06 06:15:00",   # 15 min late
            "check_out": "2026-05-06 14:00:00",
        })
        self.assertEqual(rec.late_minutes, 15,
                         msg="late_minutes must reflect actual delay from scheduled start.")
        self.assertEqual(rec.status, "late",
                         msg="Status should be 'late' when guard arrives after scheduled start.")

    def test_night_shift_hours(self):
        """
        Shift template 18:00–06:00 (next day), guard checks in/out on time.
        Weekday night (Mon→Tue) → night_hours should equal the full 12 h.
        """
        # 2026-05-04 is Monday; shift crosses into Tuesday
        slot = self._night_shift_slot("2026-05-04")
        rec = self.env["security.attendance.record"].create({
            "roster_slot_id": slot.id,
            "check_in": "2026-05-04 18:00:00",
            "check_out": "2026-05-05 06:00:00",
        })
        self.assertGreater(rec.night_hours, 0.0,
                           msg="Night shift must yield night_hours > 0.")
        self.assertTrue(rec.is_night_shift,
                        msg="is_night_shift flag must be True for overnight shift.")
        # On a Mon→Tue crossing with no public holidays, all hours should be night
        self.assertAlmostEqual(rec.night_hours, 12.0, places=1)

    def test_sunday_shift_flag(self):
        """
        Shift on a Sunday (2026-05-03) → sunday_hours > 0, saturday_hours == 0.
        """
        # 2026-05-03 is a Sunday
        slot = self._day_shift_slot("2026-05-03", start_hour=6.0, end_hour=14.0)
        rec = self.env["security.attendance.record"].create({
            "roster_slot_id": slot.id,
            "check_in": "2026-05-03 06:00:00",
            "check_out": "2026-05-03 14:00:00",
        })
        self.assertGreater(rec.sunday_hours, 0.0,
                           msg="Sunday shift must yield sunday_hours > 0.")
        self.assertEqual(rec.saturday_hours, 0.0,
                         msg="Saturday hours must be 0 on a Sunday shift.")
        self.assertEqual(rec.normal_hours, 0.0,
                         msg="Normal hours must be 0 on a Sunday shift.")
        self.assertAlmostEqual(rec.sunday_hours, 8.0, places=1,
                               msg="sunday_hours should equal the full 8-hour shift duration.")
