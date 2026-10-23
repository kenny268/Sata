"""FX week open is Sunday 17:00 America/New_York (**A-EXE-02**)."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

_NY = ZoneInfo("America/New_York")
_OPEN = (17, 0)


def current_fx_week(as_of: str) -> str:
    moment = _parse(as_of).astimezone(_NY)
    open_day = moment.date() - timedelta(days=(moment.weekday() + 1) % 7)
    if moment.weekday() == 6 and (moment.hour, moment.minute) < _OPEN:
        open_day -= timedelta(days=7)
    return open_day.isoformat()


def calendar_loaded_for(as_of: str, calendar_week: str) -> bool:
    return bool(calendar_week) and calendar_week == current_fx_week(as_of)


def _parse(as_of: str) -> datetime:
    text = as_of[:-1] + "+00:00" if as_of.endswith("Z") else as_of
    moment = datetime.fromisoformat(text)
    if moment.tzinfo is None:
        raise ValueError("fx week requires a UTC timestamp")
    return moment
