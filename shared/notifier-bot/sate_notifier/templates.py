"""Outbound message formatting (**TG-T-10** — no secrets in templates)."""

from __future__ import annotations

import re

_FORBIDDEN_IN_BODY = re.compile(
    r"(?i)(api[_-]?key|bot[_-]?token|password|secret|BEGIN (RSA |OPENSSH )?PRIVATE)",
)


def format_outbound(body: str) -> str:
    if _FORBIDDEN_IN_BODY.search(body):
        raise ValueError("template must not contain credential material")
    if len(body) > 4000:
        return body[:3997] + "..."
    return body
