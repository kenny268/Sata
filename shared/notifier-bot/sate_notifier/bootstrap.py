"""Compose entrypoint: run notifier-bot negative-auth self check."""

from __future__ import annotations

import sqlite3

from sate_factlog.log import FactLog

from sate_notifier.allowlist import Allowlist
from sate_notifier.bot import NotifierBot
from sate_notifier.commands import classify_command, parse_command


def main() -> None:
    log = FactLog(sqlite3.connect(":memory:"), writers=frozenset({"notifier-bot"}))
    bot = NotifierBot(log=log, allowlist=Allowlist(chat_id="1", user_id="owner"))
    blocked = classify_command(parse_command("/resume"))
    if blocked["class"] != "abstain":
        raise SystemExit("reduce-only policy failed")
    bot.handle_update(update_id=1, chat_id="999", user_id="intruder", text="/status", message_id="m-0")
    rows = log.poll(after_seq=0, group_scope="A", reader_id="notifier-bot")
    if not rows or rows[0].payload["resulting_event"] != "auth.failed":
        raise SystemExit("allowlist gate failed")
    digest = bot.handle_update(
        update_id=2,
        chat_id="1",
        user_id="owner",
        text="/digest",
        message_id="m-d",
    )
    if "text" not in digest:
        raise SystemExit("digest command failed")
    print("notifier-bot ok")


if __name__ == "__main__":
    main()
