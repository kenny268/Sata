"""Appendix C.1 after a kill. Resume stays closed until the steps are true."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class KillView:
    channel: str
    kill_level: str
    broker_positions: tuple[str, ...]
    system_positions: tuple[str, ...]
    fact_logged: bool
    web_passkey: bool = False
    recon_clean: bool = False
    reprovisioned: bool = False
    sim_before_live: bool = False
    cool_off_minutes: int | None = None
    cool_off_elapsed: bool = False
    preflight_passed: bool = False
    halt_level: str = ""
    killed_on: str = ""
    resume_on: str = ""


@dataclass
class C1Result:
    steps: list[str] = field(default_factory=list)
    resume_allowed: bool = False

    def executable(self) -> bool:
        required = {"confirm_kill", "compare_portal", "fact_log"}
        return required <= set(self.steps)


def run_c1(view: KillView) -> C1Result:
    result = C1Result()
    if view.channel not in {"web", "telegram", "cli"} or view.kill_level not in {"K1", "K2", "K3"}:
        result.steps.append("kill_unconfirmed")
        return result
    result.steps.append("confirm_kill")
    if view.broker_positions != view.system_positions:
        result.steps.append("portal_mismatch")
        return result
    result.steps.append("compare_portal")
    if not view.fact_logged:
        result.steps.append("fact_log_missing")
        return result
    result.steps.append("fact_log")
    if view.halt_level in {"L3", "L4"} and _same_day(view.killed_on, view.resume_on):
        result.steps.append("same_day_blocked")
        return result
    if view.kill_level == "K3":
        if not view.reprovisioned:
            result.steps.append("k3_reprovision_required")
            return result
        result.steps.append("k3_reprovisioned")
        if not view.sim_before_live:
            result.steps.append("k3_sim_before_live")
            return result
        result.steps.append("sim_before_live")
    if view.cool_off_minutes is None or view.cool_off_minutes <= 0:
        result.steps.append("cool_off_unset")
        return result
    if not view.cool_off_elapsed:
        result.steps.append("cool_off_waiting")
        return result
    result.steps.append("cool_off_complete")
    if not view.preflight_passed:
        result.steps.append("preflight_required")
        return result
    result.steps.append("preflight")
    if view.web_passkey and view.recon_clean:
        result.steps.append("resume_via_web")
        result.resume_allowed = True
    else:
        result.steps.append("resume_waits_for_web")
    return result


def _same_day(killed_on: str, resume_on: str) -> bool:
    if len(killed_on) < 10 or len(resume_on) < 10:
        return True
    return killed_on[:10] == resume_on[:10]
