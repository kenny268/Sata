"""Group A strategy engine (Phase 20). Mode-agnostic intents; no broker credentials."""

from sate_strategy_a.engine import StrategyDecision, StrategyEngine
from sate_strategy_a.intent import build_intent, validate_intent

__all__ = ["StrategyDecision", "StrategyEngine", "build_intent", "stub_intent", "validate_intent"]


def stub_intent(*, intent_id: str, instrument: str) -> dict[str, object]:
    """Backward-compatible Phase 1 stub."""
    return build_intent(
        intent_id=intent_id,
        account_mode="SIM",
        instrument=instrument,
        side="BUY",
        quantity="0",
        protective_stop="1.0700",
        strategy_id="phase-1-stub",
        created_at="1970-01-01T00:00:00Z",
    )
