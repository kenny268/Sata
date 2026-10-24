"""Telegram day-7+ reminders (**OP-01**, independent of email)."""

from __future__ import annotations


def maybe_send_reminder(*, days_without: int, reminder_days: int = 7) -> dict[str, str | bool]:
    if days_without < reminder_days:
        return {"sent": False, "channel": "telegram"}
    return {
        "sent": True,
        "channel": "telegram",
        "risk_increasing": False,
        "body": f"Check-in overdue: {days_without} day(s). Reply /alive or use the web app.",
    }
