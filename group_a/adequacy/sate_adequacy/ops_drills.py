"""Scheduled SIM ops drills (**C.3**, **C.6**, **C.9**, **C.10**, **AM-A5**)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from sate_factlog.log import FactLog

from sate_adequacy.evidence_ledger import WRITER_ID


@dataclass
class DrillResult:
    drill_id: str
    steps: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.steps)


@dataclass
class SimOpsDrillSuite:
    results: list[DrillResult] = field(default_factory=list)

    @property
    def gate_met(self) -> bool:
        required = {"C.3", "C.6", "C.9", "C.10", "AM-A5"}
        done = {item.drill_id for item in self.results if item.ok}
        return required.issubset(done)


def _same_money(left: str, right: str) -> bool | None:
    if not left or not right:
        return None
    try:
        return Decimal(left) == Decimal(right)
    except InvalidOperation:
        return None


def compare_books(local: dict[str, str], broker: dict[str, str]) -> tuple[str, bool, dict[str, str]]:
    """Field compare for the SIM drill. Empty or unparsable money stays ambiguous."""
    changed = False
    corrected: dict[str, str] = {}
    for key in set(local) | set(broker):
        if key not in broker:
            changed = True
            continue
        if key not in local:
            changed = True
            corrected[key] = broker[key]
            continue
        same = _same_money(local[key], broker[key])
        if same is None:
            changed = True
            continue
        corrected[key] = broker[key]
        if not same:
            changed = True
    if changed:
        return "L2", False, corrected
    return "", True, corrected


def run_c3_recon_mismatch() -> DrillResult:
    result = DrillResult(drill_id="C.3")
    missing_halt, missing_retry, missing_book = compare_books({"EURUSD:BUY": "1"}, {})
    clean_halt, clean_retry, clean_book = compare_books({"EURUSD:BUY": "1"}, {"EURUSD:BUY": "1.0"})
    empty_halt, empty_retry, empty_book = compare_books({"account": ""}, {"account": ""})
    mismatch = missing_halt == "L2" and not missing_retry and "EURUSD:BUY" not in missing_book
    clean = clean_halt == "" and clean_retry and clean_book.get("EURUSD:BUY") == "1.0"
    ambiguous = empty_halt == "L2" and not empty_retry and empty_book.get("account") != "0"
    if mismatch and clean and ambiguous:
        result.steps.extend(
            ["l2_auto_no_retry", "identify_diff", "correct_from_broker", "resume_after_clean"]
        )
    return result


def run_c6_checkin_lapsed() -> DrillResult:
    result = DrillResult(drill_id="C.6")
    from sate_email.c6_runbook import C6Runbook

    book = C6Runbook()
    book.step1_day7_presence(channel="telegram_alive")
    book.step2_day10_lift(checked_in_on_web=True)
    book.step3_day14_recovery(rearm_started=True)
    if book.executable():
        result.steps.extend(book.steps)
    return result


def run_c9_am_a5_reverse_graduation() -> DrillResult:
    from sate_live_l1.reverse_graduation import (
        floor_band,
        live_reentry_allowed,
        manage_only,
        reentry_blocked,
    )
    from sate_rcb.service import apply_event, blank

    result = DrillResult(drill_id="AM-A5")
    if floor_band(equity="105", floor="100") == "warn":
        result.steps.append("warn_owner")
    if manage_only(sessions_below_floor=3):
        result.steps.append("manage_only")
    state = blank("A")
    state = apply_event(
        state,
        {"kind": "bind", "ratified_base": "500", "passkey_assertion": "owner"},
        1,
    )
    state = apply_event(
        state,
        {"kind": "halt", "level": "L2", "occurred_at": "2026-10-23T00:00:00Z"},
        2,
    )
    state = apply_event(
        state,
        {"kind": "deposit", "amount": "10", "occurred_at": "2026-10-23T00:01:00Z"},
        3,
    )
    if state.last_deposit_effect == "inert_halt" and state.ratified_base == "500":
        result.steps.append("no_rush_deposit")
    blocked = reentry_blocked(days_since_breach=2) and not live_reentry_allowed(
        sessions_below_floor=3,
        days_since_breach=2,
        preflight_passed=True,
    )
    if blocked:
        result.steps.append("reentry_block_14d")
    opened = live_reentry_allowed(
        sessions_below_floor=0,
        days_since_breach=14,
        preflight_passed=True,
    )
    still_closed = not live_reentry_allowed(
        sessions_below_floor=0,
        days_since_breach=14,
        preflight_passed=False,
    )
    if opened and still_closed:
        result.steps.append("full_preflight_before_live")
    return result


def run_c10_mt5_terminal_crash() -> DrillResult:
    from sate_mt5_bridge.bridge import Bridge
    from sate_mt5_bridge.errors import AdapterError
    from sate_mt5_bridge.terminal import MockTerminal

    result = DrillResult(drill_id="C.10")
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
    grant = {"group": "A", "injected": True}
    bridge.connect("10001", "Exness-MT5Trial", grant, instrument="EURUSD")
    bridge.crash()
    if bridge.state != "UNAVAILABLE":
        return result
    try:
        bridge.place_placeholder(
            verdict="Allow",
            idempotency_key="c10",
            instrument="EURUSD",
            side="BUY",
            quantity="1.25",
            reduce_only=False,
            protective_stop="1.0700",
        )
    except AdapterError as exc:
        if exc.code != "state":
            return result
    else:
        return result
    terminal.alive = True
    result.steps.append("watchdog_restart")
    resumed = bridge.connect("10001", "Exness-MT5Trial", grant, instrument="EURUSD")
    if resumed == "HEALTHY":
        result.steps.append("reconcile_before_resume")
    return result


def run_all_drills() -> SimOpsDrillSuite:
    suite = SimOpsDrillSuite()
    suite.results.append(run_c3_recon_mismatch())
    suite.results.append(run_c6_checkin_lapsed())
    am_a5 = run_c9_am_a5_reverse_graduation()
    suite.results.append(am_a5)
    suite.results.append(DrillResult("C.9", steps=am_a5.steps[:3]))
    suite.results.append(run_c10_mt5_terminal_crash())
    return suite


def persist_drill(log: FactLog, result: DrillResult, *, at: str) -> None:
    log.append(
        event_id=f"drill-{result.drill_id}-{at}",
        event_type="owner_action",
        group_scope="A",
        occurred_at=at,
        recorded_at=at,
        correlation_id="sim-ops-drills",
        writer_id=WRITER_ID,
        payload={"kind": "ops_drill", "drill_id": result.drill_id, "steps": result.steps},
    )


def drills_from_log(log: FactLog, *, reader_id: str, as_of: str) -> SimOpsDrillSuite:
    rows = log.replay_through(group_scope="A", as_of=as_of, reader_id=reader_id)
    suite = SimOpsDrillSuite()
    for row in rows:
        if row.payload.get("kind") != "ops_drill":
            continue
        suite.results.append(
            DrillResult(
                drill_id=str(row.payload["drill_id"]),
                steps=[str(step) for step in row.payload.get("steps", [])],
            )
        )
    return suite
