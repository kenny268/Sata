"""Rate limit and mute (**TG-PO-04**, TG-T-06, TG-T-11).

INFO/NOTICE batch size is unset until the owner sets **OI-TG-05**. A LIVE desk
does not invent a cap: those messages stay held. SIM still delivers them one by one.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class DeliveryPolicy:
    info_batch_limit: int | None = None
    info_window_sec: int | None = None
    muted_until: float = 0.0
    live: bool = False
    _info_times: list[float] = field(default_factory=list)
    _held: list[str] = field(default_factory=list)
    _seen_text: list[tuple[float, str]] = field(default_factory=list)

    def should_deliver(
        self,
        severity: str,
        *,
        now: float | None = None,
        category: str = "",
        text: str = "",
    ) -> bool:
        del category
        moment = time.monotonic() if now is None else now
        normalized = severity.upper()
        if normalized in {"CRITICAL", "WARN"}:
            return True
        if normalized not in {"INFO", "NOTICE"}:
            return True
        if moment < self.muted_until:
            return False
        if not self._batch_configured():
            return not self.live
        assert self.info_window_sec is not None
        window_start = moment - self.info_window_sec
        if text and self._duplicate(text, window_start, moment):
            return False
        recent = [stamp for stamp in self._info_times if stamp >= window_start]
        self._info_times = recent
        limit = self.info_batch_limit
        assert limit is not None
        if len(recent) >= limit:
            if text:
                self._held.append(text)
            return False
        self._info_times.append(moment)
        return True

    def flush_batch(self) -> str:
        if not self._held:
            return ""
        lines = list(self._held)
        self._held.clear()
        return "[A] SUMMARY INFO\n" + "\n".join(lines)

    def mute(self, *, duration_sec: int, now: float | None = None) -> None:
        moment = time.monotonic() if now is None else now
        self.muted_until = moment + duration_sec

    def _batch_configured(self) -> bool:
        return self.info_batch_limit is not None and self.info_window_sec is not None

    def _duplicate(self, text: str, window_start: float, moment: float) -> bool:
        self._seen_text = [(stamp, body) for stamp, body in self._seen_text if stamp >= window_start]
        if any(body == text for _, body in self._seen_text):
            return True
        self._seen_text.append((moment, text))
        return False
