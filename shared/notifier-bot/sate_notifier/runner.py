"""Long-poll runner when SATE_TELEGRAM_BOT_TOKEN is configured."""

from __future__ import annotations

import os
import sqlite3
import time

from sate_factlog.log import FactLog

from sate_notifier.allowlist import Allowlist
from sate_notifier.bot import NotifierBot
from sate_notifier.polling import fetch_updates, process_updates


def runtime_config() -> dict[str, str] | None:
    """Long-poll starts only with an explicit allowlist and confirm secret.

    Chat id ``1`` and user ``owner`` are not assumed.
    """
    token = os.environ.get("SATE_TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("SATE_TELEGRAM_CHAT_ID", "").strip()
    user_id = os.environ.get("SATE_TELEGRAM_USER_ID", "").strip()
    secret = os.environ.get("SATE_NOTIFIER_CONFIRM_SECRET", "").strip()
    if not token or not chat_id or not user_id or not secret:
        return None
    return {
        "token": token,
        "chat_id": chat_id,
        "user_id": user_id,
        "confirm_secret": secret,
    }


def main() -> None:
    config = runtime_config()
    if config is None:
        print("notifier-bot runner idle (token, allowlist, or confirm secret unset)")
        return
    db = os.environ.get("SATE_FACTLOG_DB", ":memory:")
    conn = sqlite3.connect(db, check_same_thread=False)
    log = FactLog(conn, writers=frozenset({"notifier-bot"}), readers=frozenset({"notifier-bot"}))
    bot = NotifierBot(
        log=log,
        allowlist=Allowlist(chat_id=config["chat_id"], user_id=config["user_id"]),
        confirm_secret=config["confirm_secret"].encode(),
    )
    offset = 0
    for _ in range(3):
        updates = fetch_updates(token=config["token"], offset=offset, timeout_sec=1)
        offset = process_updates(bot, updates) or offset
        time.sleep(0.1)
    print("notifier-bot runner ok")


if __name__ == "__main__":
    main()
