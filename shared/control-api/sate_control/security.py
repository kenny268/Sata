"""CSRF and rate limits on control POSTs (**§13.3**)."""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass, field


@dataclass
class CsrfGuard:
    secret: bytes

    def issue(self, session_key: str) -> str:
        digest = hmac.new(self.secret, session_key.encode(), hashlib.sha256).hexdigest()
        return digest

    def validate(self, token: str | None, session_key: str) -> bool:
        if not token:
            return False
        expected = self.issue(session_key)
        return hmac.compare_digest(token, expected)


@dataclass
class RateLimiter:
    max_per_minute: int = 60
    _hits: dict[str, list[float]] = field(default_factory=dict)

    def allow(self, key: str, *, now: float | None = None) -> bool:
        moment = time.monotonic() if now is None else now
        window = moment - 60.0
        hits = [stamp for stamp in self._hits.get(key, []) if stamp >= window]
        if len(hits) >= self.max_per_minute:
            self._hits[key] = hits
            return False
        hits.append(moment)
        self._hits[key] = hits
        return True
