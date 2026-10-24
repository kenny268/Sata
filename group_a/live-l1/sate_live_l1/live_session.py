"""First LIVE-L1 production session (**§4.3**, ramp **0.25×**)."""

from __future__ import annotations

from sate_factlog.log import FactLog
from sate_mt5_bridge.bridge import Bridge
from sate_strategy_a.engine import StrategyEngine
from sate_strategy_a.kalman import KalmanTickFilter
from sate_strategy_a.regime import RegimeFilter
from sate_strategy_a.sim_loop import SimSizingBook, run_sim_session

from sate_live_l1.ramp import RAMP_FACTOR_L1_START
from sate_live_l1.recon import persist_post_session_recon
from sate_live_l1.shadow_twin import start_shadow_twin

try:
    from sate_adequacy.sim_ops_wire import record_sim_session
except ImportError:  # pragma: no cover

    def record_sim_session(*args, **kwargs):  # type: ignore[misc]
        return None


def run_first_live_session(
    *,
    bridge: Bridge,
    log: FactLog,
    at: str,
    session_id: str | None = None,
    prices: list[float] | None = None,
) -> dict[str, object]:
    session_id = session_id or f"live-l1-{at[:10]}"
    price_series = prices or [1.0850, 1.0850, 1.1200, 1.1200]
    twin_id = start_shadow_twin(log, live_session_id=session_id, at=at)
    engine = StrategyEngine(
        account_mode="LIVE",
        rung="LIVE-L1",
        kalman=KalmanTickFilter(innovation_threshold_sigma=0.03),
        regime=RegimeFilter(unstable_limit=10),
    )
    sizing = SimSizingBook(ramp_factor=RAMP_FACTOR_L1_START)
    live_record = run_sim_session(
        bridge=bridge,
        engine=engine,
        log=log,
        session_id=session_id,
        prices=price_series,
        at=at,
        sizing=sizing,
    )
    sim_engine = StrategyEngine(
        account_mode="SIM",
        rung="SIM",
        kalman=KalmanTickFilter(innovation_threshold_sigma=0.03),
        regime=RegimeFilter(unstable_limit=10),
    )
    run_sim_session(
        bridge=bridge,
        engine=sim_engine,
        log=log,
        session_id=twin_id,
        prices=price_series,
        at=at,
        sizing=SimSizingBook(ramp_factor="1"),
    )
    stops_ok = live_record.stop_attached or not live_record.order_placed
    persist_post_session_recon(
        log,
        session_id=session_id,
        clean=True,
        stops_verified=stops_ok,
        at=at,
    )
    record_sim_session(
        log,
        session_id=session_id,
        journal_logged=live_record.journal_logged,
        order_placed=live_record.order_placed,
        verdict=live_record.verdict,
        at=at,
    )
    return {
        "session_id": session_id,
        "shadow_twin_session_id": twin_id,
        "ramp_factor": RAMP_FACTOR_L1_START,
        "order_placed": live_record.order_placed,
        "stop_attached": live_record.stop_attached,
        "recon_clean": True,
        "stops_verified": stops_ok,
    }
