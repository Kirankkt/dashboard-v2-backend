"""Single source of truth for off-days (Sundays + fixed holidays).

The old app duplicated this logic across frontend and backend and warned they
had to be kept in sync. Here it lives once, on the server, and the frontend is
expected to consume it via the API (see /project/off-days) rather than copy it.
"""

from datetime import date, timedelta

# Fixed holidays as (month, day).
HOLIDAYS = {
    (12, 24),
    (12, 25),
    (12, 26),
    (12, 31),
    (1, 1),
    (3, 3),
    (3, 20),
    (4, 3),
    (4, 15),
    (5, 1),
    (5, 27),
}


def is_off(d: date) -> bool:
    """A day is off if it's a Sunday or a fixed holiday."""
    return d.weekday() == 6 or (d.month, d.day) in HOLIDAYS


def next_workday(d: date) -> date:
    """The first working day strictly after `d`."""
    nxt = d + timedelta(days=1)
    while is_off(nxt):
        nxt += timedelta(days=1)
    return nxt


def off_days_between(start: date, end: date) -> list[date]:
    """All off-days in the inclusive range [start, end]."""
    out = []
    cur = start
    while cur <= end:
        if is_off(cur):
            out.append(cur)
        cur += timedelta(days=1)
    return out
