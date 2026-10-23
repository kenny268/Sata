"""SIM → LIVE arming wizard state (**§4.3**, web-only confirm)."""

from __future__ import annotations

from dataclasses import dataclass, field
from secrets import compare_digest

from sate_control.passkey import require_passkey
from sate_control.preflight import PreflightResult, preflight_arm_live


@dataclass
class ArmingSession:
    scope: str
    phase: str = "idle"
    otp: str = ""
    arm_started_at: str = ""
    pending_reasons: list[str] = field(default_factory=list)

    def start_arm(
        self,
        *,
        passkey_assertion: str,
        preflight: PreflightResult,
        started_at: str,
        otp: str,
    ) -> dict[str, str]:
        require_passkey(assertion=passkey_assertion, action="arm_live")
        if not preflight.passed:
            self.phase = "blocked"
            self.pending_reasons = list(preflight.reasons)
            return {"status": "blocked", "reasons": ",".join(preflight.reasons)}
        self.phase = "arming"
        self.arm_started_at = started_at
        self.otp = otp
        self.pending_reasons = []
        return {"status": "arming", "delay_hours": "24"}

    def confirm(
        self,
        *,
        code: str,
        passkey_assertion: str,
        now: str = "",
        skip_delay: bool = False,
    ) -> dict[str, str]:
        require_passkey(assertion=passkey_assertion, action="confirm_live")
        if self.phase != "arming":
            raise ValueError("no arming session is active")
        if not skip_delay and now and self.arm_started_at:
            from sate_live_l1.arming_delay import arming_delay_elapsed

            if not arming_delay_elapsed(started_at=self.arm_started_at, as_of=now):
                raise ValueError("arming_delay_not_elapsed")
        if not compare_digest(code, self.otp):
            raise ValueError("otp mismatch")
        self.phase = "live_l1"
        return {"status": "live_l1", "mode": "LIVE-L1"}

    def cancel(self) -> dict[str, str]:
        self.phase = "idle"
        self.otp = ""
        self.pending_reasons = []
        return {"status": "cancelled"}


def build_preflight(**kwargs: object) -> PreflightResult:
    return preflight_arm_live(**kwargs)  # type: ignore[arg-type]
