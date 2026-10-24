"""Run control-api HTTP on the private network."""

from __future__ import annotations

import os
import sqlite3

from sate_control.auth import Session
from sate_control.http_server import ControlHttpServer
from sate_control.router import ControlApi
from sate_factlog.log import FactLog


def main() -> None:
    host = os.environ.get("SATE_CONTROL_BIND", "127.0.0.1")
    port = int(os.environ.get("SATE_CONTROL_PORT", "8080"))
    db = os.environ.get("SATE_FACTLOG_DB", ":memory:")
    conn = sqlite3.connect(db, check_same_thread=False)  # ThreadingHTTPServer
    log = FactLog(conn, writers=frozenset({"control-api"}), readers=frozenset({"control-api"}))
    api = ControlApi(log=log, session=Session(principal="owner", group_scope="A"))
    ControlHttpServer(api).serve(host, port)


if __name__ == "__main__":
    main()
