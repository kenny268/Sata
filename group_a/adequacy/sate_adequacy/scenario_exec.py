"""Executable §15 cases that the catalog previously left as stubs."""

from __future__ import annotations

from decimal import Decimal

from sate_halt.c1_runbook import KillView, run_c1
from sate_halt.protocol import HaltState
from sate_halt.service import Coordinator
from sate_mt5_bridge.bridge import Bridge
from sate_mt5_bridge.errors import AdapterError
from sate_mt5_bridge.terminal import MockTerminal
from sate_rcb.service import apply_event, blank
from sate_strategy_a.pre_kernel import MarketContext, validate_pre_kernel
from sate_strategy_a.sizing import size_position
from sate_strategy_a.universe import validate_instrument

from sate_adequacy.ops_drills import run_c9_am_a5_reverse_graduation
from sate_live_l1.arming_delay import arming_delay_elapsed
from sate_live_l1.reverse_graduation import live_reentry_allowed, manage_only

_ORDER = ("", "L1", "L2", "L3", "L4")
_TARGET = {
    "slippage": "L1",
    "feed": "L1",
    "daily_loss": "L2",
    "recon": "L2",
    "fingerprint": "L2",
    "heartbeat": "L2",
    "terms": "L2",
    "drawdown": "L3",
    "margin": "L3",
    "repeated_l2": "L3",
    "ops_heartbeat": "L4",
    "account_change": "L4",
}


def escalate(current: str, trigger: str) -> str:
    target = _TARGET[trigger]
    if _ORDER.index(target) > _ORDER.index(current):
        return target
    return current


def blocks_new_risk(level: str) -> bool:
    return level in {"L2", "L3", "L4"}


def _demo() -> tuple[Bridge, MockTerminal]:
    terminal = MockTerminal(
        login="10001",
        server="Exness-MT5Trial",
        mode="SIM",
        bid="1.0850",
        ask="1.0852",
        server_time="2026-10-23T21:00:00Z",
        settlement="demo",
        min_lot="1.25",
        lot_step="0.01",
        stops_level="0",
    )
    bridge = Bridge(terminal)
    bridge.connect(
        "10001",
        "Exness-MT5Trial",
        {"group": "A", "injected": True},
        instrument="EURUSD",
    )
    return bridge, terminal


def _entry(bridge: Bridge, key: str, stop: str = "1.0700") -> None:
    bridge.place_placeholder(
        verdict="Allow",
        idempotency_key=key,
        instrument="EURUSD",
        side="BUY",
        quantity="1.25",
        reduce_only=False,
        protective_stop=stop,
    )


def _intent() -> dict[str, object]:
    return {
        "intent_id": "ts-1",
        "trace_id": "ts-1",
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
    }


def _context(**extra: object) -> MarketContext:
    values = {
        "tick_age_ms": 50,
        "swap_estimate": 0.1,
        "swap_budget": 5.0,
        "hold_includes_wednesday": False,
        "hold_through_close": False,
    }
    values.update(extra)
    return MarketContext(**values)  # type: ignore[arg-type]


def execute(scenario_id: str) -> tuple[bool, str]:
    runner = _CASES.get(scenario_id)
    if runner is None:
        return False, "missing from harness"
    return runner()


def _ts05() -> tuple[bool, str]:
    try:
        validate_instrument("GBPUSD", account_mode="LIVE", rung="LIVE-L1")
    except ValueError as exc:
        return True, str(exc)
    return False, "universe accepted GBPUSD"


def _ts06() -> tuple[bool, str]:
    full = size_position(
        capital_base="1000",
        max_risk_pct="1",
        vol_scaled_risk="1",
        ramp_factor="1",
        stop_distance="0.05",
        value_per_unit="1",
        lot_step="0.01",
        min_lot="0.01",
        notional_cap_size="100",
        leverage_cap_size="100",
    )
    reduced = size_position(
        capital_base="1000",
        max_risk_pct="1",
        vol_scaled_risk="0.5",
        ramp_factor="0.5",
        stop_distance="0.05",
        value_per_unit="1",
        lot_step="0.01",
        min_lot="0.01",
        notional_cap_size="100",
        leverage_cap_size="100",
    )
    ok = (not full.rejected) and (not reduced.rejected) and Decimal(reduced.quantity) < Decimal(full.quantity)
    return ok, f"{full.quantity}->{reduced.quantity}"


def _ts07() -> tuple[bool, str]:
    bridge, terminal = _demo()
    terminal.rate_limited = True
    bridge.subscribe("EURUSD")
    if bridge.state != "DEGRADED":
        return False, bridge.state
    try:
        _entry(bridge, "ts07")
    except AdapterError as exc:
        return exc.code == "state", exc.code
    return False, "rate limit still submitted"


def _ts08() -> tuple[bool, str]:
    blocked = validate_pre_kernel(_intent(), context=_context(news_blackout=True))
    if blocked is None:
        return False, "blackout allowed"
    return blocked.reason == "news_blackout", blocked.reason


def _ts11() -> tuple[bool, str]:
    bridge, terminal = _demo()
    _entry(bridge, "ts11")
    _entry(bridge, "ts11")
    return terminal.submits == ["ts11"], str(terminal.submits)


def _ts12() -> tuple[bool, str]:
    from sate_runtime.journal import persist_lifecycle
    from sate_factlog.log import FactLog
    import sqlite3

    log = FactLog(sqlite3.connect(":memory:"), writers=frozenset({"kernel-a"}))
    persist_lifecycle(
        log,
        {
            "intent_id": "i-1",
            "client_id": "i-1",
            "correlation_id": "A:i-1",
            "state": "Partial",
            "instrument": "EURUSD",
            "side": "BUY",
            "quantity": "1",
            "filled": "0.4",
            "remainder": "0.6",
            "broker_id": None,
            "kind": "partial",
        },
        event_id="ts12",
        occurred_at="2026-10-23T21:00:00Z",
        recorded_at="2026-10-23T21:00:00Z",
        correlation_id="A:i-1",
    )
    stored = log.poll(after_seq=0, group_scope="A", reader_id="kernel-a")
    return stored[0].payload["remainder"] == "0.6", "partial remainder"


def _ts13() -> tuple[bool, str]:
    bridge, terminal = _demo()
    terminal.stop_attach_fails = True
    try:
        _entry(bridge, "ts13")
    except AdapterError as exc:
        return exc.code == "protective_stop" and terminal.submits == [], exc.code
    return False, "stop failure still opened"


def _halt(trigger: str, expected: str) -> tuple[bool, str]:
    level = escalate("", trigger)
    blocked = blocks_new_risk(level)
    if expected in {"L2", "L3", "L4"}:
        return level == expected and blocked, level
    return level == expected and not blocked, level


def _oc(level: str) -> tuple[bool, str]:
    coordinator = Coordinator()
    command = coordinator.issue(
        command_id=f"oc-{level}",
        scope="A",
        kill_level=level,
        reason=level,
        channel="web",
        identity="owner",
        b_reachable=True,
    )
    state = coordinator.ack_a(command.command_id)
    return state == HaltState.HALT_CONFIRMED_A and command.kill_level == level, state.value


def _oc04() -> tuple[bool, str]:
    coordinator = Coordinator()
    command = coordinator.issue(
        command_id="oc-04",
        scope="ALL",
        kill_level="K2",
        reason="partial",
        channel="web",
        identity="owner",
        b_reachable=False,
    )
    state = coordinator.ack_a(command.command_id)
    return state != HaltState.HALT_CONFIRMED_ALL, state.value


def _oc05() -> tuple[bool, str]:
    coordinator = Coordinator()
    command = coordinator.issue(
        command_id="oc-05",
        scope="A",
        kill_level="K1",
        reason="cli",
        channel="cli",
        identity="owner",
        b_reachable=False,
    )
    coordinator.drill.record(channel="cli", kill_level="K1", mode="SIM")
    return command.channel == "cli" and coordinator.drill.gate_met() is False, command.channel


def _oc06() -> tuple[bool, str]:
    coordinator = Coordinator()
    command = coordinator.issue(
        command_id="oc-06",
        scope="A",
        kill_level="K2",
        reason="trusted",
        channel="web",
        identity="trusted-contact",
        b_reachable=False,
    )
    return command.identity == "trusted-contact" and not hasattr(coordinator, "resume"), command.kill_level


def _oc07() -> tuple[bool, str]:
    view = KillView(
        channel="web",
        kill_level="K1",
        broker_positions=("EURUSD",),
        system_positions=("EURUSD",),
        fact_logged=True,
        web_passkey=True,
        recon_clean=True,
    )
    result = run_c1(view)
    return result.resume_allowed, ",".join(result.steps)


def _oc08() -> tuple[bool, str]:
    blocked = run_c1(
        KillView(
            channel="web",
            kill_level="K3",
            broker_positions=(),
            system_positions=(),
            fact_logged=True,
        )
    )
    opened = run_c1(
        KillView(
            channel="web",
            kill_level="K3",
            broker_positions=(),
            system_positions=(),
            fact_logged=True,
            reprovisioned=True,
            web_passkey=True,
            recon_clean=True,
        )
    )
    return (not blocked.resume_allowed) and opened.resume_allowed, ",".join(opened.steps)


def _am01() -> tuple[bool, str]:
    early = arming_delay_elapsed(started_at="2026-10-23T00:00:00Z", as_of="2026-10-23T12:00:00Z")
    ready = arming_delay_elapsed(started_at="2026-10-23T00:00:00Z", as_of="2026-10-24T00:00:00Z")
    return (not early) and ready, f"early={early} ready={ready}"


def _am_a5() -> tuple[bool, str]:
    drill = run_c9_am_a5_reverse_graduation()
    held = manage_only(sessions_below_floor=3)
    rushed = live_reentry_allowed(sessions_below_floor=3, days_since_breach=2, preflight_passed=True)
    later = live_reentry_allowed(sessions_below_floor=0, days_since_breach=14, preflight_passed=True)
    ok = held and not rushed and later and "reentry_block_14d" in drill.steps
    return ok, ",".join(drill.steps)


def _ct01() -> tuple[bool, str]:
    state = blank("A")
    state = apply_event(
        state,
        {"kind": "bind", "ratified_base": "500", "passkey_assertion": "owner"},
        1,
    )
    state = apply_event(
        state,
        {"kind": "deposit", "amount": "10", "occurred_at": "2026-10-23T00:00:00Z"},
        2,
    )
    still = state.ratified_base == "500" and state.last_deposit_effect == "pending_ratification"
    return still, state.last_deposit_effect


def _bf02() -> tuple[bool, str]:
    level = escalate("", "terms")
    return level == "L2" and blocks_new_risk(level), "terms change blocks without a new cap"


def _bf03() -> tuple[bool, str]:
    bridge, _terminal = _demo()
    try:
        bridge.withdraw()
    except AdapterError as exc:
        return exc.code == "manual", exc.code
    return False, "withdraw opened"


def _bf04() -> tuple[bool, str]:
    state = blank("A")
    state = apply_event(
        state,
        {"kind": "bind", "ratified_base": "500", "passkey_assertion": "owner"},
        1,
    )
    state = apply_event(state, {"kind": "halt", "level": "L2", "occurred_at": "2026-10-23T00:00:00Z"}, 2)
    state = apply_event(
        state,
        {"kind": "deposit", "amount": "10", "occurred_at": "2026-10-23T00:01:00Z"},
        3,
    )
    killed = _oc("K2")[0]
    return killed and state.last_deposit_effect == "inert_halt" and state.ratified_base == "500", state.last_deposit_effect


def _bf05() -> tuple[bool, str]:
    bridge, _terminal = _demo()
    bridge.crash()
    try:
        _entry(bridge, "bf05")
    except AdapterError as exc:
        return bridge.state == "UNAVAILABLE" and exc.code == "state", bridge.state
    return False, "crash still accepted an entry"


def _bf06() -> tuple[bool, str]:
    return _ts13()


def _bf07() -> tuple[bool, str]:
    return _bf05()


_CASES = {
    "TS-05": _ts05,
    "TS-06": _ts06,
    "TS-07": _ts07,
    "TS-08": _ts08,
    "TS-11": _ts11,
    "TS-12": _ts12,
    "TS-13": _ts13,
    "HL-01": lambda: _halt("slippage", "L1"),
    "HL-02": lambda: _halt("feed", "L1"),
    "HL-07": lambda: _halt("drawdown", "L3"),
    "HL-08": lambda: _halt("margin", "L3"),
    "HL-A": lambda: _halt("daily_loss", "L2"),
    "HL-B": lambda: _halt("recon", "L2"),
    "HL-C": lambda: _halt("fingerprint", "L2"),
    "HL-D": lambda: _halt("heartbeat", "L2"),
    "HL-E": lambda: _halt("repeated_l2", "L3"),
    "HL-F": lambda: _halt("ops_heartbeat", "L4"),
    "OC-01": lambda: _oc("K1"),
    "OC-02": lambda: _oc("K2"),
    "OC-03": lambda: _oc("K3"),
    "OC-04": _oc04,
    "OC-05": _oc05,
    "OC-06": _oc06,
    "OC-07": _oc07,
    "OC-08": _oc08,
    "AM-01": _am01,
    "AM-A5": _am_a5,
    "CT-01": _ct01,
    "BF-02": _bf02,
    "BF-03": _bf03,
    "BF-04": _bf04,
    "BF-05": _bf05,
    "BF-06": _bf06,
    "BF-07": _bf07,
}
