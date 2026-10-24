"""Compose entrypoint: exercise the configured email provider."""

import os

from sate_email.appendix_d import email_provider_assumption
from sate_email.provider import ConsoleProvider, load_provider_from_env
from sate_email.reminder import ReminderScheduler


def main() -> None:
    provider = load_provider_from_env()
    ReminderScheduler(provider).maybe_send(to="owner@example.com", days_without=7)
    transport = os.environ.get("SATE_EMAIL_TRANSPORT", "console").strip().lower()
    if transport not in {"console", "smtp"}:
        raise SystemExit("SATE_EMAIL_TRANSPORT must be console or smtp")
    assumption = email_provider_assumption(transport=transport)
    if isinstance(provider, ConsoleProvider):
        if not provider.sent:
            raise SystemExit("expected a day-7 reminder")
        print(provider.sent[0]["subject"])
    else:
        print(assumption["assumption_id"])


if __name__ == "__main__":
    main()
