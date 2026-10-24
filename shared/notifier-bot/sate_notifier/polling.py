"""Optional Telegram getUpdates loop (token from env, not stored in repo)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable

from sate_notifier.bot import NotifierBot

Handler = Callable[[dict[str, object]], None]


def fetch_updates(*, token: str, offset: int, timeout_sec: int = 30) -> list[dict[str, object]]:
    url = f"https://api.telegram.org/bot{token}/getUpdates?timeout={timeout_sec}&offset={offset}"
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec + 5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError:
        return []
    if not payload.get("ok"):
        return []
    result = payload.get("result")
    return result if isinstance(result, list) else []


def process_updates(bot: NotifierBot, updates: list[dict[str, object]]) -> int:
    next_offset = 0
    for update in updates:
        update_id = int(update.get("update_id", 0))
        next_offset = max(next_offset, update_id + 1)
        message = update.get("message")
        if not isinstance(message, dict):
            continue
        chat = message.get("chat") or {}
        user = message.get("from") or {}
        text = str(message.get("text", ""))
        bot.handle_update(
            update_id=update_id,
            chat_id=str(chat.get("id", "")),
            user_id=str(user.get("id", "")),
            text=text,
            message_id=str(message.get("message_id", "")),
        )
    return next_offset


def run_once(bot: NotifierBot, *, token: str | None = None) -> int:
    token = token or os.environ.get("SATE_TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        return 0
    updates = fetch_updates(token=token, offset=0, timeout_sec=0)
    return process_updates(bot, updates)
