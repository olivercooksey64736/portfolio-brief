"""
NYSE trading-day gate.

Answers one question: should the portfolio brief run right now?

Holidays are computed from rules rather than hardcoded, so this needs no
annual maintenance. Early closes (1pm ET on Jul 3, the day after
Thanksgiving, and Christmas Eve) are irrelevant to a pre-open brief and
are deliberately not modelled.

Usage in a scheduled task:
    python3 nyse_gate.py            -> prints RUN or SKIP:<reason>, exit 0/1
"""

from datetime import date, timedelta
from zoneinfo import ZoneInfo
from datetime import datetime
import sys

NY = ZoneInfo("America/New_York")


def easter_sunday(year: int) -> date:
    """Anonymous Gregorian algorithm."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """n-th <weekday> of month. weekday: Mon=0 .. Sun=6."""
    d = date(year, month, 1)
    offset = (weekday - d.weekday()) % 7
    return d + timedelta(days=offset + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    if month == 12:
        d = date(year, 12, 31)
    else:
        d = date(year, month + 1, 1) - timedelta(days=1)
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def _observed(d: date, is_new_years: bool = False) -> date | None:
    """
    NYSE Rule 7.2: a Saturday holiday closes the preceding Friday, a Sunday
    holiday closes the following Monday. Exception: New Year's Day falling on
    a Saturday does NOT close the preceding Friday, because that Friday is the
    last trading day of the year. Returns None when there is no closure.
    """
    if d.weekday() == 5:                       # Saturday
        return None if is_new_years else d - timedelta(days=1)
    if d.weekday() == 6:                       # Sunday
        return d + timedelta(days=1)
    return d


def nyse_holidays(year: int) -> set[date]:
    out = set()
    for d in (
        _observed(date(year, 1, 1), is_new_years=True),
        _nth_weekday(year, 1, 0, 3),           # MLK Day
        _nth_weekday(year, 2, 0, 3),           # Washington's Birthday
        easter_sunday(year) - timedelta(days=2),   # Good Friday
        _last_weekday(year, 5, 0),             # Memorial Day
        _observed(date(year, 6, 19)),          # Juneteenth
        _observed(date(year, 7, 4)),           # Independence Day
        _nth_weekday(year, 9, 0, 1),           # Labor Day
        _nth_weekday(year, 11, 3, 4),          # Thanksgiving
        _observed(date(year, 12, 25)),         # Christmas
    ):
        if d is not None:
            out.add(d)
    return out


def is_trading_day(d: date) -> bool:
    return d.weekday() < 5 and d not in nyse_holidays(d.year)


def should_run(now: datetime | None = None) -> tuple[bool, str]:
    """True only on a trading day, in the 09:00 ET hour (30 min pre-open)."""
    now = (now or datetime.now(NY)).astimezone(NY)
    if not is_trading_day(now.date()):
        return False, f"NYSE closed on {now.date()}"
    if now.hour != 9:
        return False, f"not the 09:00 ET slot (local hour {now.hour:02d})"
    return True, f"trading day, {now:%Y-%m-%d %H:%M %Z}"


if __name__ == "__main__":
    ok, why = should_run()
    print("RUN" if ok else f"SKIP:{why}")
    sys.exit(0 if ok else 1)
