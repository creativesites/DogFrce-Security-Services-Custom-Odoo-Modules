"""
Unit tests for split_shift_by_boundaries.

No database required — pure Python unittest.TestCase.
Run via: ./scripts/run-tests.sh security_attendance
"""

import unittest
from datetime import date, datetime

from odoo.addons.security_attendance.utils.shift_split import split_shift_by_boundaries


def _dt(date_str: str, hour: int, minute: int = 0) -> datetime:
    """Helper: build a naive datetime from 'YYYY-MM-DD' + hour/minute."""
    y, m, d = (int(p) for p in date_str.split("-"))
    return datetime(y, m, d, hour, minute)


class TestSplitShiftByBoundaries(unittest.TestCase):

    # ------------------------------------------------------------------ #
    # Basic day-type classification                                        #
    # ------------------------------------------------------------------ #

    def test_normal_weekday_day_shift(self):
        """Monday 06:00–18:00 is entirely normal hours."""
        result = split_shift_by_boundaries(
            _dt("2026-05-04", 6),   # Monday
            _dt("2026-05-04", 18),
            public_holidays=[],
        )
        self.assertAlmostEqual(result["normal_hours"], 12.0)
        self.assertAlmostEqual(result["sunday_hours"], 0.0)
        self.assertAlmostEqual(result["public_holiday_hours"], 0.0)
        self.assertAlmostEqual(result["saturday_hours"], 0.0)
        self.assertAlmostEqual(result["night_hours"], 0.0)

    def test_sunday_day_shift(self):
        """Sunday 06:00–18:00 is entirely sunday hours."""
        result = split_shift_by_boundaries(
            _dt("2026-05-03", 6),   # Sunday
            _dt("2026-05-03", 18),
            public_holidays=[],
        )
        self.assertAlmostEqual(result["sunday_hours"], 12.0)
        self.assertAlmostEqual(result["normal_hours"], 0.0)
        self.assertAlmostEqual(result["night_hours"], 0.0)

    def test_saturday_day_shift(self):
        """Saturday 06:00–18:00 is entirely saturday hours."""
        result = split_shift_by_boundaries(
            _dt("2026-05-02", 6),   # Saturday
            _dt("2026-05-02", 18),
            public_holidays=[],
        )
        self.assertAlmostEqual(result["saturday_hours"], 12.0)
        self.assertAlmostEqual(result["normal_hours"], 0.0)
        self.assertAlmostEqual(result["night_hours"], 0.0)

    def test_public_holiday_day_shift(self):
        """A day-shift on a public holiday is entirely public_holiday hours."""
        ph = date(2026, 3, 21)  # Independence Day
        result = split_shift_by_boundaries(
            _dt("2026-03-21", 6),
            _dt("2026-03-21", 18),
            public_holidays=[ph],
        )
        self.assertAlmostEqual(result["public_holiday_hours"], 12.0)
        self.assertAlmostEqual(result["normal_hours"], 0.0)

    # ------------------------------------------------------------------ #
    # Night shift — weekday only                                          #
    # ------------------------------------------------------------------ #

    def test_weekday_night_shift_no_crossing(self):
        """Monday 18:00–Tuesday 06:00 → all night hours (both days are weekdays)."""
        result = split_shift_by_boundaries(
            _dt("2026-05-04", 18),  # Monday night
            _dt("2026-05-05", 6),   # Tuesday morning
            public_holidays=[],
        )
        self.assertAlmostEqual(result["night_hours"], 12.0)
        self.assertAlmostEqual(result["normal_hours"], 0.0)
        self.assertAlmostEqual(result["sunday_hours"], 0.0)
        self.assertAlmostEqual(result["saturday_hours"], 0.0)

    def test_friday_night_into_saturday(self):
        """
        Friday 18:00–Saturday 06:00.
        Friday 18:00–midnight = night (6 h).
        Saturday 00:00–06:00 = saturday (6 h).
        Saturday > Night priority.
        """
        result = split_shift_by_boundaries(
            _dt("2026-05-01", 18),  # Friday
            _dt("2026-05-02", 6),   # Saturday
            public_holidays=[],
        )
        self.assertAlmostEqual(result["night_hours"], 6.0)
        self.assertAlmostEqual(result["saturday_hours"], 6.0)
        self.assertAlmostEqual(result["normal_hours"], 0.0)
        self.assertAlmostEqual(result["sunday_hours"], 0.0)

    def test_saturday_night_into_sunday(self):
        """
        Saturday 18:00–Sunday 06:00.
        Saturday 18:00–midnight = saturday (6 h).  saturday > night.
        Sunday 00:00–06:00 = sunday (6 h).          sunday > night.
        night_hours = 0.
        """
        result = split_shift_by_boundaries(
            _dt("2026-05-02", 18),  # Saturday
            _dt("2026-05-03", 6),   # Sunday
            public_holidays=[],
        )
        self.assertAlmostEqual(result["saturday_hours"], 6.0)
        self.assertAlmostEqual(result["sunday_hours"], 6.0)
        self.assertAlmostEqual(result["night_hours"], 0.0)
        self.assertAlmostEqual(result["normal_hours"], 0.0)

    def test_sunday_night_into_monday(self):
        """
        Sunday 18:00–Monday 06:00.
        Sunday 18:00–midnight = sunday (6 h).  sunday > night.
        Monday 00:00–06:00 = night (6 h).
        """
        result = split_shift_by_boundaries(
            _dt("2026-05-03", 18),  # Sunday
            _dt("2026-05-04", 6),   # Monday
            public_holidays=[],
        )
        self.assertAlmostEqual(result["sunday_hours"], 6.0)
        self.assertAlmostEqual(result["night_hours"], 6.0)
        self.assertAlmostEqual(result["normal_hours"], 0.0)

    # ------------------------------------------------------------------ #
    # Public holiday crossings                                            #
    # ------------------------------------------------------------------ #

    def test_night_shift_crossing_into_public_holiday(self):
        """
        Monday 18:00–Tuesday 06:00 where Tuesday is a public holiday.
        Monday 18:00–midnight = night (6 h).
        Tuesday 00:00–06:00 = public_holiday (6 h).  PH > night.
        """
        ph = date(2026, 5, 5)  # Tuesday
        result = split_shift_by_boundaries(
            _dt("2026-05-04", 18),  # Monday
            _dt("2026-05-05", 6),   # Tuesday (PH)
            public_holidays=[ph],
        )
        self.assertAlmostEqual(result["night_hours"], 6.0)
        self.assertAlmostEqual(result["public_holiday_hours"], 6.0)
        self.assertAlmostEqual(result["normal_hours"], 0.0)

    def test_public_holiday_into_normal_day(self):
        """
        PH day shift 06:00–18:00 → all public_holiday.
        (Day shift so no night boundary crossed.)
        """
        ph = date(2026, 3, 21)
        result = split_shift_by_boundaries(
            _dt("2026-03-21", 6),
            _dt("2026-03-21", 18),
            public_holidays=[ph],
        )
        self.assertAlmostEqual(result["public_holiday_hours"], 12.0)
        self.assertAlmostEqual(result["night_hours"], 0.0)

    # ------------------------------------------------------------------ #
    # Total hours invariant                                               #
    # ------------------------------------------------------------------ #

    def test_total_hours_equals_shift_duration(self):
        """Sum of all buckets must always equal the shift duration in hours."""
        cases = [
            (_dt("2026-05-04", 6), _dt("2026-05-04", 18), []),
            (_dt("2026-05-04", 18), _dt("2026-05-05", 6), []),
            (_dt("2026-05-01", 18), _dt("2026-05-02", 6), []),
            (_dt("2026-05-02", 18), _dt("2026-05-03", 6), []),
            (_dt("2026-05-03", 18), _dt("2026-05-04", 6), []),
            (_dt("2026-05-04", 18), _dt("2026-05-05", 6), [date(2026, 5, 5)]),
        ]
        for start, end, phs in cases:
            result = split_shift_by_boundaries(start, end, phs)
            total = sum(result.values())
            expected = (end - start).total_seconds() / 3600.0
            self.assertAlmostEqual(
                total, expected,
                msg=f"Total mismatch for shift {start}–{end}: {total} != {expected}",
            )

    # ------------------------------------------------------------------ #
    # Edge cases                                                          #
    # ------------------------------------------------------------------ #

    def test_zero_duration_shift(self):
        """Start equals end → all buckets zero."""
        t = _dt("2026-05-04", 6)
        result = split_shift_by_boundaries(t, t, public_holidays=[])
        self.assertEqual(sum(result.values()), 0.0)

    def test_partial_shift_late_arrival(self):
        """
        Normal weekday day shift, guard arrives 1 hour late.
        07:00–18:00 (11 h) → 11 normal hours, 0 night.
        """
        result = split_shift_by_boundaries(
            _dt("2026-05-04", 7),   # 1 hour late
            _dt("2026-05-04", 18),
            public_holidays=[],
        )
        self.assertAlmostEqual(result["normal_hours"], 11.0)
        self.assertAlmostEqual(result["night_hours"], 0.0)

    def test_split_at_night_boundary_exact(self):
        """
        Shift 06:00–18:00 hits exactly the 18:00 boundary at the end —
        no night hours should appear (boundary is exclusive on the right).
        """
        result = split_shift_by_boundaries(
            _dt("2026-05-04", 6),
            _dt("2026-05-04", 18),
            public_holidays=[],
        )
        self.assertAlmostEqual(result["night_hours"], 0.0)
        self.assertAlmostEqual(result["normal_hours"], 12.0)
