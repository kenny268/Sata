"""Compose entrypoint: smoke the control-api router."""

from __future__ import annotations

import sqlite3
import tempfile

from sate_control.auth import Session
from sate_control.router import ControlApi
from sate_factlog.log import FactLog


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        log = FactLog(
            sqlite3.connect(f"{tmp}/fact.db"),
            writers=frozenset({"control-api"}),
            readers=frozenset({"control-api"}),
        )
        api = ControlApi(log=log, session=Session(principal="owner", group_scope="A"))
        state = api.dispatch("GET", "/state", {"scope": "A", "mode": "SIM"})
        if state["mode"] != "SIM":
            raise SystemExit("control-api state route failed")
        token = api.issue_csrf()["csrf_token"]
        passkey = "AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGWFiY2RlZmdoaWprbG1ub3BxcnN0dXZ3eHk"
        api.dispatch(
            "POST",
            "/checkin",
            {"channel": "web_passkey", "passkey_assertion": passkey},
            csrf_token=token,
        )
        rows = log.poll(after_seq=0, group_scope="A", reader_id="control-api")
        if not any(row.event_type == "owner_action" for row in rows):
            raise SystemExit("expected owner_action audit row")
        print("control-api ok")


if __name__ == "__main__":
    main()
