"""Away mode defers to web passkey (**TG-PO-08**, TG-S-20)."""

from __future__ import annotations

WEB_AWAY_URL = "/checkin"

_AWAY_DURATIONS = (7, 14, 21, 30)


def away_menu(*, max_away_days: int = 30) -> dict[str, object]:
    options = [str(day) for day in _AWAY_DURATIONS if day <= max_away_days]
    return {
        "class": "abstain",
        "message": "Select away days in Telegram, then complete away mode in the web app with passkey.",
        "web_url": WEB_AWAY_URL,
        "duration_buttons": options + ["Cancel"],
        "max_away_days": str(max_away_days),
    }
