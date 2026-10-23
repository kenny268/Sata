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
    if view.kill_level == "K3":
        if not view.reprovisioned:
            result.steps.append("k3_reprovision_required")
            return result
        result.steps.append("k3_reprovisioned")
    if view.web_passkey and view.recon_clean:
        result.steps.append("resume_via_web")
        result.resume_allowed = True
    else:
        result.steps.append("resume_waits_for_web")
    return result
