"""Automated §15 scenario harness for CI/staging."""

from __future__ import annotations

from dataclasses import dataclass, field

from sate_cognitive.gate import trading_advisory_multiplier
from sate_control.preflight import preflight_arm_live
from sate_halt.service import Coordinator
from sate_mt5_bridge.bridge import Bridge
from sate_mt5_bridge.terminal import MockTerminal
from sate_strategy_a.engine import StrategyEngine
from sate_strategy_a.kalman import KalmanTickFilter
from sate_strategy_a.mp_infra import PromotionInfraChecklist
from sate_strategy_a.regime import RegimeFilter
from sate_strategy_a.scenarios import (
    ts01_valid_signal_to_intent,
    ts02_cognitive_down_kalman_continues,
    ts03_abstain_zero_view,
    ts04_untradeable_at_capital,
    ts09_swap_guard_blocks,
    ts10_stale_ticks_block,
)

from sate_adequacy.scenario_catalog import SCENARIO_FAMILIES, all_scenario_ids
from sate_adequacy.scenario_exec import execute


@dataclass
class ScenarioOutcome:
    scenario_id: str
    ok: bool
    detail: str = ""
    execution: str = "executable"


@dataclass
class ScenarioSuiteResult:
    outcomes: list[ScenarioOutcome] = field(default_factory=list)

    @property
    def green(self) -> bool:
        return all(item.ok for item in self.outcomes)

    def export(self) -> dict[str, object]:
        executable = sum(1 for item in self.outcomes if item.execution == "executable")
        return {
            "green": self.green,
            "total": len(self.outcomes),
            "executable": executable,
            "stub": len(self.outcomes) - executable,
            "failed": [item.scenario_id for item in self.outcomes if not item.ok],
        }


def _engine() -> StrategyEngine:
    return StrategyEngine(
        account_mode="SIM",
        rung="SIM",
        kalman=KalmanTickFilter(innovation_threshold_sigma=0.03),
        regime=RegimeFilter(unstable_limit=10),
    )


def _run_ts() -> list[ScenarioOutcome]:
    engine = _engine()
    prices = [1.0850, 1.0850] + [1.1200] * 8
    outcomes: list[ScenarioOutcome] = []
    ts01 = ts01_valid_signal_to_intent(engine, prices=prices)
    outcomes.append(
        ScenarioOutcome("TS-01", "pre_kernel_ok" in ts01.steps, ",".join(ts01.steps) or "no steps")
    )
    outcomes.append(
        ScenarioOutcome(
            "TS-02",
            "zero_advisory_kalman_ok" in ts02_cognitive_down_kalman_continues().steps,
            "zero advisory",
        )
    )
    ts03 = ts03_abstain_zero_view()
    outcomes.append(ScenarioOutcome("TS-03", ts03.category == "ABSTAIN", ts03.reason))
    ts04 = ts04_untradeable_at_capital()
    outcomes.append(
        ScenarioOutcome(
            "TS-04",
            "untradeable_rejected" in ts04.steps,
            ",".join(ts04.steps) or "missing reject",
        )
    )
    ts09 = ts09_swap_guard_blocks()
    outcomes.append(
        ScenarioOutcome("TS-09", "swap_rejected" in ts09.steps, ",".join(ts09.steps) or "no swap block")
    )
    ts10 = ts10_stale_ticks_block()
    outcomes.append(
        ScenarioOutcome("TS-10", "stale_blocked" in ts10.steps, ",".join(ts10.steps) or "stale")
    )
    done = {item.scenario_id for item in outcomes}
    for scenario_id in SCENARIO_FAMILIES["TS"]:
        if scenario_id in done:
            continue
        ok, detail = execute(scenario_id)
        outcomes.append(ScenarioOutcome(scenario_id, ok, detail))
    return outcomes


def _run_hl() -> list[ScenarioOutcome]:
    outcomes: list[ScenarioOutcome] = []
    coordinator = Coordinator()
    command = coordinator.issue(
        command_id="hl-stub-1",
        scope="A",
        kill_level="K1",
        reason="hl catalog",
        channel="web",
        identity="owner",
        b_reachable=False,
    )
    coordinator.ack_a(command.command_id)
    outcomes.append(
        ScenarioOutcome("HL-01", coordinator.mark_b_unreachable(command.command_id) is not None, "halt path")
    )
    done = {item.scenario_id for item in outcomes}
    for scenario_id in SCENARIO_FAMILIES["HL"]:
        if scenario_id in done:
            continue
        ok, detail = execute(scenario_id)
        outcomes.append(ScenarioOutcome(scenario_id, ok, detail))
    return outcomes


def _run_oc() -> list[ScenarioOutcome]:
    coordinator = Coordinator()
    command = coordinator.issue(
        command_id="oc-01",
        scope="A",
        kill_level="K1",
        reason="oc-01",
        channel="web",
        identity="owner",
        b_reachable=True,
    )
    coordinator.ack_a(command.command_id)
    return [
        ScenarioOutcome("OC-01", command.kill_level == "K1", "K1 issued"),
        *[
            ScenarioOutcome(scenario_id, *execute(scenario_id))
            for scenario_id in SCENARIO_FAMILIES["OC"]
            if scenario_id != "OC-01"
        ],
    ]


def _run_am() -> list[ScenarioOutcome]:
    blocked = preflight_arm_live(
        scope="A",
        clean_recon=False,
        constitution_pinned=True,
        mode="SIM",
    )
    ok = preflight_arm_live(
        scope="A",
        clean_recon=True,
        constitution_pinned=True,
        mode="SIM",
    )
    outcomes = [
        ScenarioOutcome("AM-02", not blocked.passed and "recon_not_clean" in blocked.reasons, "preflight"),
        ScenarioOutcome("AM-03", ok.passed, "clean preflight"),
    ]
    for scenario_id in SCENARIO_FAMILIES["AM"]:
        if scenario_id in {"AM-02", "AM-03"}:
            continue
        ok, detail = execute(scenario_id)
        outcomes.append(ScenarioOutcome(scenario_id, ok, detail))
    return outcomes


def _run_ct() -> list[ScenarioOutcome]:
    zero = trading_advisory_multiplier(account_mode="LIVE") == 0.0
    ok, detail = execute("CT-01")
    return [
        ScenarioOutcome("CT-08", zero, "advisory zero on budget path"),
        ScenarioOutcome("CT-01", ok, detail),
    ]


def _run_bf() -> list[ScenarioOutcome]:
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
    outcomes = [
        ScenarioOutcome("BF-01", bridge.state == "DISCONNECTED", "no connect"),
    ]
    for scenario_id in SCENARIO_FAMILIES["BF"]:
        if scenario_id == "BF-01":
            continue
        ok, detail = execute(scenario_id)
        outcomes.append(ScenarioOutcome(scenario_id, ok, detail))
    return outcomes


def _run_mp() -> list[ScenarioOutcome]:
    checklist = PromotionInfraChecklist()
    checklist.record_mp01_bootstrap_gate()
    checklist.record_mp02_shadow_decisions()
    checklist.record_mp03_no_loosen()
    ok = checklist.gate_met()
    return [
        ScenarioOutcome("MP-01", ok, "promotion infra"),
        ScenarioOutcome("MP-02", ok, "shadow"),
        ScenarioOutcome("MP-03", ok, "no loosen"),
    ]


def run_scenario_suite() -> ScenarioSuiteResult:
    outcomes: list[ScenarioOutcome] = []
    outcomes.extend(_run_ts())
    outcomes.extend(_run_hl())
    outcomes.extend(_run_oc())
    outcomes.extend(_run_am())
    outcomes.extend(_run_ct())
    outcomes.extend(_run_bf())
    outcomes.extend(_run_mp())
    expected = set(all_scenario_ids())
    seen = {item.scenario_id for item in outcomes}
    for missing in sorted(expected - seen):
        outcomes.append(ScenarioOutcome(missing, False, "missing from harness"))
    return ScenarioSuiteResult(outcomes=outcomes)


def main() -> None:
    result = run_scenario_suite()
    if not result.green:
        raise SystemExit(f"scenario suite failed: {result.export()}")
    print("scenario suite green", result.export())


if __name__ == "__main__":
    main()
