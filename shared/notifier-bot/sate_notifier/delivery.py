"""Rate limit and mute (**TG-PO-04**, TG-T-06, TG-T-11)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

_NO_BATCH = frozenset({"HALT", "KILL", "ERROR", "HEALTH"})


@dataclass
class DeliveryPolicy:
    info_batch_limit: int = 20
    info_window_sec: int = 60
    muted_until: float = 0.0
    _info_times: list[float] = field(default_factory=list)

    def should_deliver(self, severity: str, *, now: float | None = None, category: str = "") -> bool:
        moment = time.monotonic() if now is None else now
        normalized = severity.upper()
        if category.upper() in _NO_BATCH:
            return True
        if normalized == "CRITICAL":
            return True
        if normalized == "WARN":
            return True
        if moment < self.muted_until and normalized in {"INFO", "NOTICE"}:
            return False
        if normalized in {"INFO", "NOTICE"}:
            window_start = moment - self.info_window_sec
            recent = [stamp for stamp in self._info_times if stamp >= window_start]
            self._info_times = recent
            if len(recent) >= self.info_batch_limit:
                return False
            self._info_times.append(moment)
        return True

    def mute(self, *, duration_sec: int, now: float | None = None) -> None:
        moment = time.monotonic() if now is None else now
        self.muted_until = moment + duration_sec
