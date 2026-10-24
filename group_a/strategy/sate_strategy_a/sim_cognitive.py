"""SIM shadow hooks — ingest advisory without trading authority (**Phase 21**)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from sate_cognitive.ingest import ingest_signal
from sate_cognitive.shadow import ShadowAccumulator
from sate_cognitive.shadow_log import persist_ingest
from sate_factlog.log import FactLog

from sate_strategy_a.cognitive_wire import advisory_view_for_blend


@dataclass
class SimCognitiveShadow:
    public_key: bytes
    week: str
    accumulator: ShadowAccumulator
    log: FactLog | None = None
    account_mode: str = "SIM"
    _pending_outcome_id: str | None = field(default=None, repr=False)

    def begin_session(
        self,
        *,
        session_id: str,
        signal: dict[str, object] | None,
        now: str,
    ) -> float | None:
        if signal is None:
            self.accumulator.record_ingest(ok=False, signal_id=f"{session_id}-missing", shadow_q=0.0)
            return None
        result = ingest_signal(
            signal,
            now=now,
            public_key=self.public_key,
            account_mode=self.account_mode,
        )
        signal_id = str(signal.get("signal_id", session_id))
        self.accumulator.record_ingest(
            ok=result.ok,
            signal_id=signal_id,
            shadow_q=result.shadow_q,
            shadow_c=result.shadow_c,
        )
        if self.log is not None:
            persist_ingest(
                self.log,
                event_id=f"adv-ingest-{signal_id}",
                signal_id=signal_id,
                result=result,
                at=now,
                correlation_id=session_id,
            )
        self._pending_outcome_id = signal_id if result.ok else None
        return advisory_view_for_blend(result)

    def end_session(self, *, prices: list[float]) -> None:
        pending = self._pending_outcome_id
        if not pending or len(prices) < 2:
            return
        move = prices[-1] - prices[0]
        outcome = 0.0 if move == 0 else math.copysign(1.0, move)
        self.accumulator.attach_outcome(pending, outcome)


def signed_return_sign(prices: list[float]) -> float:
    if len(prices) < 2:
        return 0.0
    move = prices[-1] - prices[0]
    return 0.0 if move == 0 else math.copysign(1.0, move)
