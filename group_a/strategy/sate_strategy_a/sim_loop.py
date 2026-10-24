"""Continuous SIM trading loop with bridge integration."""

from __future__ import annotations

from dataclasses import dataclass

from sate_factlog.log import FactLog
from sate_mt5_bridge.bridge import Bridge
from sate_runtime.journal import persist_verdict, submit_persisted

from sate_strategy_a.decision_journal import persist_decision_journal
from sate_strategy_a.engine import StrategyEngine
from sate_strategy_a.evidence import SimSessionRecord, SimWeekEvidence
from sate_strategy_a.pre_kernel import MarketContext
from sate_strategy_a.sim_cognitive import SimCognitiveShadow
from sate_strategy_a.vol_risk import vol_scaled_risk_pct


@dataclass(frozen=True)
class SimSizingBook:
    capital_base: str = "500000"
    max_risk_pct: str = "0.5"
    vol_scaled_risk: str = "0.5"
    vol_atr: str = "0.0010"
    baseline_atr: str = "0.0010"
    ramp_factor: str = "1"
    stop_distance: str = "0.0050"
    value_per_unit: str = "100000"
    lot_step: str = "0.01"
    min_lot: str = "1.25"
    notional_cap_size: str = "5"
    leverage_cap_size: str = "5"


def _sizing_dict(book: SimSizingBook) -> dict[str, str]:
    scaled = vol_scaled_risk_pct(
        base_pct=book.max_risk_pct,
        atr=book.vol_atr,
        baseline_atr=book.baseline_atr,
    )
    return {
        "capital_base": book.capital_base,
        "max_risk_pct": book.max_risk_pct,
        "vol_scaled_risk": scaled,
        "ramp_factor": book.ramp_factor,
        "stop_distance": book.stop_distance,
        "value_per_unit": book.value_per_unit,
        "lot_step": book.lot_step,
        "min_lot": book.min_lot,
        "notional_cap_size": book.notional_cap_size,
        "leverage_cap_size": book.leverage_cap_size,
    }


def run_sim_session(
    *,
    bridge: Bridge,
    engine: StrategyEngine,
    log: FactLog,
    session_id: str,
    prices: list[float],
    at: str,
    sizing: SimSizingBook | None = None,
    cognitive_shadow: SimCognitiveShadow | None = None,
    session_signal: dict[str, object] | None = None,
) -> SimSessionRecord:
    book = sizing or SimSizingBook()
    if bridge.state in {"DISCONNECTED", "UNAVAILABLE"}:
        raise ValueError("bridge must be connected before SIM session")
    bridge.poll()
    journal_logged = False
    verdict_label = "Abstain"
    order_placed = False
    stop_attached = False
    intent_id: str | None = None
    last_reason = "no_signal"
    advisory_view: float | None = None
    if cognitive_shadow is not None:
        advisory_view = cognitive_shadow.begin_session(
            session_id=session_id,
            signal=session_signal,
            now=at,
        )
    for tick, price in enumerate(prices):
        decision = engine.evaluate_tick(
            intent_id=f"{session_id}-i-{tick}",
            instrument="EURUSD",
            price=price,
            bid=str(bridge.quote.get("bid", "1.0850")),
            advisory_view=advisory_view if tick == 0 else None,
            sizing_inputs=_sizing_dict(book),
            created_at=at,
            market_context=MarketContext(
                tick_age_ms=100,
                swap_estimate=0.2,
                swap_budget=5.0,
                hold_includes_wednesday=False,
                hold_through_close=False,
            ),
        )
        if decision.abstain or decision.intent is None:
            last_reason = decision.reason or last_reason
            continue
        intent = decision.intent
        intent_id = str(intent["intent_id"])
        persist_decision_journal(
            log,
            intent_id=intent_id,
            hypothesis=f"kalman tick {tick}",
            action=str(intent["side"]),
            at=at,
        )
        journal_logged = True
        verdict = {
            "intent_id": intent_id,
            "kernel_version": "0.20.0",
            "constitution_version": "1",
            "decision": "Allow",
            "approved_quantity": None,
            "reject_reason": None,
            "checks": [{"name": "sim", "passed": True, "value": "", "limit": ""}],
            "halt_level": None,
            "kill_state": None,
            "latency_us": 10,
            "issued_at": at,
        }
        persist_verdict(
            log,
            verdict,
            event_id=f"v-{intent_id}",
            occurred_at=at,
            recorded_at=at,
            correlation_id=intent_id,
        )
        submit_persisted(verdict, persisted=True)
        order = bridge.place_placeholder(
            verdict="Allow",
            idempotency_key=intent_id,
            instrument="EURUSD",
            side=str(intent["side"]),
            quantity=str(intent["quantity"]),
            reduce_only=False,
            protective_stop=str(intent["protective_stop"]),
        )
        verdict_label = "Allow"
        order_placed = True
        stop_attached = order.stop_attached
        break
    if not journal_logged:
        persist_decision_journal(
            log,
            intent_id=f"{session_id}-abstain",
            hypothesis=last_reason,
            action="abstain",
            at=at,
        )
        journal_logged = True
        verdict_label = "Abstain"
    if cognitive_shadow is not None:
        cognitive_shadow.end_session(prices=prices)
    return SimSessionRecord(
        session_id=session_id,
        journal_logged=journal_logged,
        verdict=verdict_label,
        order_placed=order_placed,
        stop_attached=stop_attached,
        intent_id=intent_id,
    )


def run_sim_weeks(
    *,
    bridge: Bridge,
    engine: StrategyEngine,
    log: FactLog,
    weeks: int,
    sessions_per_week: int,
    price_series: list[float],
    at: str,
    cognitive_shadow: SimCognitiveShadow | None = None,
    session_signals: list[dict[str, object] | None] | None = None,
) -> SimWeekEvidence:
    evidence = SimWeekEvidence()
    cursor = 0
    signal_index = 0
    for week in range(weeks):
        week_sessions: list[SimSessionRecord] = []
        for session in range(sessions_per_week):
            session_id = f"w{week + 1}-s{session + 1}"
            window = price_series[cursor : cursor + 12]
            cursor = (cursor + 3) % max(len(price_series) - 12, 1)
            if len(window) < 12:
                window = price_series[-12:]
            session_signal = None
            if session_signals is not None and signal_index < len(session_signals):
                session_signal = session_signals[signal_index]
            signal_index += 1
            week_sessions.append(
                run_sim_session(
                    bridge=bridge,
                    engine=engine,
                    log=log,
                    session_id=session_id,
                    prices=window,
                    at=at,
                    cognitive_shadow=cognitive_shadow,
                    session_signal=session_signal,
                )
            )
        evidence.record_week(week_sessions)
    return evidence
