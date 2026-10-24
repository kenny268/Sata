"""Constitution quiet hours — CRITICAL bypasses (**TG-07**)."""

from __future__ import annotations


def parse_window(window: str) -> tuple[int, int]:
    start_text, end_text = window.split("-", 1)
    return _hhmm_to_minutes(start_text.strip()), _hhmm_to_minutes(end_text.strip())


def _hhmm_to_minutes(text: str) -> int:
    hour, minute = text.split(":", 1)
    return int(hour) * 60 + int(minute)


def in_quiet_hours(*, now_minutes: int, window: str) -> bool:
    start, end = parse_window(window)
    if start <= end:
        return start <= now_minutes < end
    return now_minutes >= start or now_minutes < end


def deliver_during_quiet_hours(severity: str, *, quiet: bool) -> bool:
    if severity.upper() == "CRITICAL":
        return True
    return not quiet
