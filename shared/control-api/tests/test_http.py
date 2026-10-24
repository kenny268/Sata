"""HTTP control boundary and CSRF."""

from __future__ import annotations

import json
import sqlite3
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from threading import Thread

from sate_control.auth import Session
from sate_control.http_server import ControlHttpServer
from sate_control.router import ControlApi
from sate_factlog.log import FactLog

_PASSKEY = "AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGWFiY2RlZmdoaWprbG1ub3BxcnN0dXZ3eHk"


class HttpServerTests(unittest.TestCase):
    def test_get_state_and_post_require_csrf(self) -> None:
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        log = FactLog(conn, writers=frozenset({"control-api"}), readers=frozenset({"control-api"}))
        api = ControlApi(log=log, session=Session(principal="owner", group_scope="A"))
        server = ControlHttpServer(api)
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), _handler_factory(server))
        port = httpd.server_address[1]
        thread = Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            client = HTTPConnection("127.0.0.1", port, timeout=5)
            client.request("GET", "/state?scope=A&mode=SIM")
            response = client.getresponse()
            self.assertEqual(response.status, 200)
            client.request("GET", "/csrf")
            csrf_response = client.getresponse()
            token = json.loads(csrf_response.read())["csrf_token"]
            client.request(
                "POST",
                "/checkin",
                body=json.dumps({"channel": "web_passkey", "passkey_assertion": _PASSKEY}).encode(),
                headers={"Content-Type": "application/json", "X-CSRF-Token": token},
            )
            self.assertEqual(client.getresponse().status, 200)
            client.request(
                "POST",
                "/checkin",
                body=json.dumps({"channel": "web_passkey", "passkey_assertion": _PASSKEY}).encode(),
                headers={"Content-Type": "application/json", "X-CSRF-Token": "bad"},
            )
            self.assertEqual(client.getresponse().status, 403)
        finally:
            httpd.shutdown()
            conn.close()


from sate_control.http_server import _handler_factory  # noqa: E402


if __name__ == "__main__":
    unittest.main()
