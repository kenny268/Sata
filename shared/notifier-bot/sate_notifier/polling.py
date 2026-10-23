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


def process_updates(
    bot: NotifierBot,
    updates: list[dict[str, object]],
    *,
    sender: Callable[[dict[str, object]], None] | None = None,
) -> int:
    next_offset = 0
    for update in updates:
        update_id = int(update.get("update_id", 0))
        next_offset = max(next_offset, update_id + 1)
        parsed = _parse_update(update)
        if parsed is None:
            continue
        result = bot.handle_update(
            update_id=update_id,
            chat_id=parsed["chat_id"],
            user_id=parsed["user_id"],
            text=parsed["text"],
            message_id=parsed["message_id"],
        )
        if sender is not None and result.get("status") != "discarded":
            sender(result)
    return next_offset


def _parse_update(update: dict[str, object]) -> dict[str, str] | None:
    message = update.get("message")
    if isinstance(message, dict):
        chat = message.get("chat") if isinstance(message.get("chat"), dict) else {}
        user = message.get("from") if isinstance(message.get("from"), dict) else {}
        return {
            "chat_id": str(chat.get("id", "")),
            "user_id": str(user.get("id", "")),
            "text": str(message.get("text", "")),
            "message_id": str(message.get("message_id", "")),
        }
    callback = update.get("callback_query")
    if not isinstance(callback, dict):
        return None
    message = callback.get("message") if isinstance(callback.get("message"), dict) else {}
    chat = message.get("chat") if isinstance(message.get("chat"), dict) else {}
    user = callback.get("from") if isinstance(callback.get("from"), dict) else {}
    data = str(callback.get("data") or "")
    return {
        "chat_id": str(chat.get("id", "")),
        "user_id": str(user.get("id", "")),
        "text": data,
        "message_id": str(callback.get("id", message.get("message_id", ""))),
    }


def run_once(bot: NotifierBot, *, token: str | None = None) -> int:
    token = token or os.environ.get("SATE_TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        return 0
    updates = fetch_updates(token=token, offset=0, timeout_sec=0)
    return process_updates(bot, updates)
