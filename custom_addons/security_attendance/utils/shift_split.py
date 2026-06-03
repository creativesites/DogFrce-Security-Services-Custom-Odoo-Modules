"""
Shift hour bucket splitter.

Splits a contiguous shift window into pay-category buckets, handling
midnight crossings and shifts that span multiple calendar days.

Priority order (highest wins per minute-segment):
  public_holiday > sunday > saturday > night > normal

"Night" means weekday hours (Mon–Fri) between 18:00 and 06:00.
Saturday/Sunday/public-holiday hours absorb any night overlap — the
premium of the day type is already higher and categories do not stack.

This is a pure Python utility with no Odoo ORM dependency so it can be
imported by any module and called from unit tests without a database.
"""

from datetime import date, datetime, time, timedelta

# Configurable night window boundaries (hour of day, 24-hour clock).
# Default: night starts at 18:00 and ends at 06:00.
_NIGHT_START = 18
_NIGHT_END = 6


def split_shift_by_boundaries(
    shift_start: datetime,
    shift_end: datetime,
    public_holidays: list,
    night_start_hour: int = _NIGHT_START,
    night_end_hour: int = _NIGHT_END,
) -> dict:
    """
    Return hours in each pay category for a shift spanning any time range.

    Args:
        shift_start: Shift start as a timezone-naive datetime.
        shift_end:   Shift end as a timezone-naive datetime (may be next day).
        public_holidays: Iterable of ``datetime.date`` objects that are
            public holidays. Dates outside the shift range are ignored.
        night_start_hour: Hour (0–23) at which night premium begins.
            Default 18 (18:00).
        night_end_hour: Hour (0–23) at which night premium ends.
            Default 6 (06:00).

    Returns:
        dict with float keys:
            normal_hours, sunday_hours, public_holiday_hours,
            saturday_hours, night_hours
        All values are hours (float).  Sum equals the total shift duration.
    """
    buckets = {
        "normal_hours": 0.0,
        "sunday_hours": 0.0,
        "public_holiday_hours": 0.0,
        "saturday_hours": 0.0,
        "night_hours": 0.0,
    }

    if shift_start >= shift_end:
        return buckets

    ph_set = set(public_holidays)

    def _category(dt: datetime) -> str:
        d = dt.date()
        if d in ph_set:
            return "public_holiday"
        wd = d.weekday()  # 0 = Monday … 5 = Saturday … 6 = Sunday
        if wd == 6:
            return "sunday"
        if wd == 5:
            return "saturday"
        h = dt.hour
        if h >= night_start_hour or h < night_end_hour:
            return "night"
        return "normal"

    # Build the list of internal boundary datetimes within the shift.
    # A boundary occurs at every midnight, night_end_hour, and night_start_hour
    # between shift_start (exclusive) and shift_end (exclusive).
    boundary_hours = sorted({0, night_end_hour, night_start_hour})
    boundaries: list[datetime] = []
    current_day = shift_start.date()
    end_day = shift_end.date()
    while current_day <= end_day:
        for h in boundary_hours:
            candidate = datetime.combine(current_day, time(h, 0, 0))
            if shift_start < candidate < shift_end:
                boundaries.append(candidate)
        current_day += timedelta(days=1)
    boundaries.sort()

    # Accumulate hours per segment.
    points = [shift_start] + boundaries + [shift_end]
    for i in range(len(points) - 1):
        seg_start = points[i]
        seg_end = points[i + 1]
        seg_hours = (seg_end - seg_start).total_seconds() / 3600.0
        if seg_hours <= 0:
            continue
        category = _category(seg_start)
        buckets[f"{category}_hours"] += seg_hours

    return buckets
