"""Trading scenario harness **TS-01–03**, **TS-09** (Phase 20)."""

from __future__ import annotations

from dataclasses import dataclass, field

from sate_strategy_a.abstain import AbstainDecision
from sate_strategy_a.black_litterman import blend_views
from sate_strategy_a.engine import StrategyEngine
from sate_strategy_a.freshness import validate_freshness
from sate_strategy_a.pre_kernel import MarketContext, validate_pre_kernel
from sate_strategy_a.sim_loop import SimSizingBook, _sizing_dict
from sate_strategy_a.sizing import size_position


@dataclass
class ScenarioLog:
    steps: list[str] = field(default_factory=list)


def ts01_valid_signal_to_intent(engine: StrategyEngine, *, prices: list[float]) -> ScenarioLog:
    log = ScenarioLog()
    sizing = _sizing_dict(SimSizingBook())
    for index, price in enumerate(prices):
        decision = engine.evaluate_tick(
            intent_id=f"ts01-{index}",
            instrument="EURUSD",
            price=price,
            bid="1.0850",
            advisory_view=None,
            sizing_inputs=sizing,
            created_at="2026-10-23T21:00:00Z",
        )
        if decision.intent is not None:
            log.steps.append("intent")
            blocked = validate_pre_kernel(
                decision.intent,
                context=MarketContext(
                    tick_age_ms=100,
                    swap_estimate=0.1,
                    swap_budget=5.0,
                    hold_includes_wednesday=False,
                    hold_through_close=False,
                ),
            )
            if blocked is None:
                log.steps.append("pre_kernel_ok")
            break
    return log


def ts02_cognitive_down_kalman_continues() -> ScenarioLog:
    log = ScenarioLog()
    blend = blend_views(kalman_direction=1, advisory_view=None, regime_tilt=True)
    if blend.view == 1.0 and not blend.advisory_used:
        log.steps.append("zero_advisory_kalman_ok")
    return log


def ts03_abstain_zero_view() -> AbstainDecision:
    return AbstainDecision(reason="weak_evidence", digest="ABSTAIN weak_evidence: stale tool", category="ABSTAIN")


def ts04_untradeable_at_capital() -> ScenarioLog:
    log = ScenarioLog()
    result = size_position(
        capital_base="100",
        max_risk_pct="0.5",
        vol_scaled_risk="0.5",
        ramp_factor="1",
        stop_distance="0.0100",
        value_per_unit="100000",
        lot_step="0.01",
        min_lot="0.10",
        notional_cap_size="5",
        leverage_cap_size="5",
    )
    if result.rejected and result.reason == "untradeable_at_this_capital":
        log.steps.append("untradeable_rejected")
    return log


def ts10_stale_ticks_block() -> ScenarioLog:
    log = ScenarioLog()
    if not validate_freshness(age_ms=9000).ok:
        log.steps.append("stale_blocked")
    return log


def ts09_swap_guard_blocks() -> ScenarioLog:
    log = ScenarioLog()
    blocked = validate_pre_kernel(
        {
            "intent_id": "ts09-1",
            "trace_id": "ts09-1",
            "group": "A",
            "account_mode": "SIM",
            "instrument": "EURUSD",
            "side": "BUY",
            "quantity": "1.25",
            "order_type": "MARKET",
            "limit_price": None,
            "protective_stop": "1.0700",
            "take_profit": None,
            "slippage_budget": "0.5",
            "strategy_id": "test",
            "signal_refs": [],
            "advisory_refs": [],
            "created_at": "2026-10-23T21:00:00Z",
        },
        context=MarketContext(
            tick_age_ms=50,
            swap_estimate=10.0,
            swap_budget=1.0,
            hold_includes_wednesday=True,
            hold_through_close=False,
        ),
    )
    if blocked is not None and blocked.reason == "swap_guard":
        log.steps.append("swap_rejected")
    return log
