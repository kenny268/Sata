from __future__ import annotations

import sqlite3
import unittest

from sate_control.auth import Session
from sate_control.router import ControlApi
from sate_factlog.log import FactLog
from sate_rcb.errors import RcbError
from sate_rcb.service import blank
from sate_rcb.sourced import submit_bind

_PASSKEY = "AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGWFiY2RlZmdoaWprbG1ub3BxcnN0dXZ3eHk"
_NOW = "2026-10-23T00:00:00Z"


class RatifyWireTests(unittest.TestCase):
    def test_capital_ratify_calls_rcb_service(self) -> None:
        conn = sqlite3.connect(":memory:")
        writers = frozenset({"control-api", "rcb"})
        log = FactLog(conn, writers=writers, readers=writers)
        state = submit_bind(
            log,
            blank("A"),
            "100",
            passkey_assertion=_PASSKEY,
            event_id="bind-1",
            occurred_at=_NOW,
            recorded_at=_NOW,
            correlation_id="bind-1",
        )
        api = ControlApi(
            log=log,
            session=Session(principal="owner", group_scope="A"),
            rcb_state=state,
            now=_NOW,
        )
        token = api.issue_csrf()["csrf_token"]
        with self.assertRaises(RcbError):
            api.dispatch(
                "POST",
                "/capital/ratify",
                {"passkey_assertion": _PASSKEY},
                csrf_token=token,
            )
