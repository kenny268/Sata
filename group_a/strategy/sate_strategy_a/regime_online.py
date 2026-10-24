"""Online regime stability hint **A-SIG-02** (lightweight; full GMM/HMM is research-gated)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OnlineRegime:
    vol_threshold: float = 0.0005
    _returns: list[float] = field(default_factory=list)

    def observe(self, price: float) -> bool:
        if not self._returns:
            self._returns.append(price)
            return True
        previous = self._returns[-1]
        move = abs(price - previous)
        self._returns.append(price)
        if len(self._returns) > 50:
            self._returns.pop(0)
        return move <= self.vol_threshold
