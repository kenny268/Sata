"""stdlib HTTP binding for control-api (**§13.2** security boundary)."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable
from urllib.parse import parse_qs, urlparse

from sate_control.router import ControlApi
from sate_control.security import CsrfGuard, RateLimiter

try:
    from sate_monitoring.security_events import SecurityEventRecorder
except ImportError:  # pragma: no cover
    SecurityEventRecorder = None  # type: ignore[misc, assignment]


class ControlHttpServer:
    def __init__(
        self,
        api: ControlApi,
        *,
        csrf: CsrfGuard | None = None,
        rate_limiter: RateLimiter | None = None,
        security_recorder: object | None = None,
    ) -> None:
        self._api = api
        self._csrf = csrf or CsrfGuard(secret=b"sate-control-api-phase17")
        self._limiter = rate_limiter or RateLimiter()
        self._api.csrf = self._csrf
        if security_recorder is not None:
            self._security = security_recorder
        elif SecurityEventRecorder is not None:
            self._security = SecurityEventRecorder()
        else:
            self._security = None

    def serve(self, host: str, port: int) -> None:
        factory = _handler_factory(self)
        server = ThreadingHTTPServer((host, port), factory)
        server.serve_forever()

    def handle(
        self,
        method: str,
        path: str,
        body: dict[str, object],
        headers: dict[str, str],
    ) -> tuple[int, dict]:
        client = headers.get("x-forwarded-for") or headers.get("x-real-ip") or "local"
        if not self._limiter.allow(client):
            if self._security is not None:
                self._security.rate_limited(client)  # type: ignore[union-attr]
            return 429, {"error": "rate_limited"}
        csrf_token = headers.get("x-csrf-token") or str(body.get("csrf_token", ""))
        try:
            if method == "GET" and path == "/csrf":
                payload = self._api.issue_csrf()
                return 200, payload
            result = self._api.dispatch(method, path, body, csrf_token=csrf_token)
            return 200, result
        except PermissionError as exc:
            if self._security is not None:
                self._security.permission_denied(str(exc))  # type: ignore[union-attr]
            return 403, {"error": str(exc)}
        except ValueError as exc:
            message = str(exc)
            if self._security is not None and "global scope" in message.lower():
                self._security.scope_violation(message)  # type: ignore[union-attr]
            return 400, {"error": message}


def _handler_factory(server: ControlHttpServer) -> Callable[..., type[BaseHTTPRequestHandler]]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format: str, *_args: object) -> None:
            return

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            query = {key: values[0] for key, values in parse_qs(parsed.query).items() if values}
            status, payload = server.handle("GET", parsed.path, query, _headers(self))
            _respond(self, status, payload)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                body = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                _respond(self, 400, {"error": "invalid json"})
                return
            if not isinstance(body, dict):
                _respond(self, 400, {"error": "invalid json"})
                return
            status, payload = server.handle("POST", parsed.path, body, _headers(self))
            _respond(self, status, payload)

    return Handler


def _headers(handler: BaseHTTPRequestHandler) -> dict[str, str]:
    return {key.lower(): value for key, value in handler.headers.items()}


def _respond(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)
