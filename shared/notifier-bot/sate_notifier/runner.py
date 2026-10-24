"""Long-poll runner when SATE_TELEGRAM_BOT_TOKEN is configured."""

from __future__ import annotations

import os
import sqlite3
import time

from sate_factlog.log import FactLog

from sate_notifier.allowlist import Allowlist
from sate_notifier.bot import NotifierBot
from sate_notifier.polling import fetch_updates, process_updates


def main() -> None:
    token = os.environ.get("SATE_TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("SATE_TELEGRAM_CHAT_ID", "1")
    user_id = os.environ.get("SATE_TELEGRAM_USER_ID", "owner")
    db = os.environ.get("SATE_FACTLOG_DB", ":memory:")
    conn = sqlite3.connect(db, check_same_thread=False)
    log = FactLog(conn, writers=frozenset({"notifier-bot"}), readers=frozenset({"notifier-bot"}))
    bot = NotifierBot(log=log, allowlist=Allowlist(chat_id=chat_id, user_id=user_id))
    if not token:
        print("notifier-bot runner idle (no token)")
        return
    offset = 0
    for _ in range(3):
        updates = fetch_updates(token=token, offset=offset, timeout_sec=1)
        offset = process_updates(bot, updates) or offset
        time.sleep(0.1)
    print("notifier-bot runner ok")


if __name__ == "__main__":
    main()
