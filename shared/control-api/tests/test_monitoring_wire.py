"""HTTP boundary emits monitoring security events."""

from __future__ import annotations

import json
import sqlite3
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from threading import Thread

from sate_control.auth import Session
from sate_control.http_server import ControlHttpServer, _handler_factory
from sate_control.router import ControlApi
from sate_factlog.log import FactLog
from sate_monitoring.security_events import SecurityEventRecorder

_PASSKEY = "AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGWFiY2RlZmdoaWprbG1ub3BxcnN0dXZ3eHk"


class MonitoringWireTests(unittest.TestCase):
    def test_csrf_failure_records_auth_alert(self) -> None:
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        log = FactLog(conn, writers=frozenset({"control-api"}), readers=frozenset({"control-api"}))
        api = ControlApi(log=log, session=Session(principal="owner", group_scope="A"))
        recorder = SecurityEventRecorder()
        server = ControlHttpServer(api, security_recorder=recorder)
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), _handler_factory(server))
        port = httpd.server_address[1]
        thread = Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            client = HTTPConnection("127.0.0.1", port, timeout=5)
            client.request(
                "POST",
                "/checkin",
                body=json.dumps({"channel": "web_passkey", "passkey_assertion": _PASSKEY}).encode(),
                headers={"Content-Type": "application/json", "X-CSRF-Token": "invalid"},
            )
            self.assertEqual(client.getresponse().status, 403)
            self.assertTrue(recorder.on_call.dispatches)
            self.assertEqual(recorder.on_call.dispatches[0][1].code, "control_auth_failure")
        finally:
            httpd.shutdown()
            conn.close()


if __name__ == "__main__":
    unittest.main()
