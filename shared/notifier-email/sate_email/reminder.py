"""Day-7+ reminders independent of Telegram (**A-CHK-03**)."""

from __future__ import annotations

from sate_email.provider import EmailProvider


def send_reminder(provider: EmailProvider, *, to: str, days_without: int) -> None:
    provider.send(
        to=to,
        subject="SATE Group A check-in reminder",
        body=f"Owner check-in overdue: {days_without} day(s) without presence.",
    )


class ReminderScheduler:
    def __init__(self, provider: EmailProvider, *, reminder_days: int = 7) -> None:
        self._provider = provider
        self._reminder_days = reminder_days

    def maybe_send(self, *, to: str, days_without: int) -> bool:
        if days_without < self._reminder_days:
            return False
        send_reminder(self._provider, to=to, days_without=days_without)
        return True
