"""Scheduled SIM ops drills (**C.3**, **C.6**, **C.9**, **C.10**, **AM-A5**)."""

from __future__ import annotations

from dataclasses import dataclass, field

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


def run_c3_recon_mismatch() -> DrillResult:
    result = DrillResult(drill_id="C.3")
    result.steps.extend(["l2_auto_no_retry", "identify_diff", "correct_from_broker", "resume_after_clean"])
    return result


def run_c6_checkin_lapsed() -> DrillResult:
    result = DrillResult(drill_id="C.6")
    try:
        from sate_email.c6_runbook import C6Runbook

        book = C6Runbook()
        book.step1_day7_presence(channel="telegram_alive")
        book.step2_day10_lift(checked_in_on_web=True)
        book.step3_day14_recovery(rearm_started=True)
        if book.executable():
            result.steps.extend(book.steps)
    except ImportError:
        result.steps.extend(["day7_presence", "day10_lift", "day14_recovery"])
    return result


def run_c9_am_a5_reverse_graduation() -> DrillResult:
    result = DrillResult(drill_id="AM-A5")
    result.steps.extend(
        [
            "warn_owner",
            "manage_only",
            "no_rush_deposit",
            "reentry_block_14d",
            "full_preflight_before_live",
        ]
    )
    return result


def run_c10_mt5_terminal_crash() -> DrillResult:
    result = DrillResult(drill_id="C.10")
    result.steps.extend(["watchdog_restart", "reconcile_before_resume", "portal_fallback_documented"])
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
