"""control-api route dispatcher (**§13.2**)."""

from __future__ import annotations

from dataclasses import dataclass, field

from sate_control.arming import ArmingSession
from sate_control.audit import persist_owner_action
from sate_control.auth import Session, authorize_control, authorize_read
from sate_control.checkin_service import apply_away, apply_checkin
from sate_control.kill import validate_kill, validate_resume
from sate_control.passkey import require_passkey
from sate_control.preflight import preflight_arm_live
from sate_control.reporting import reject_global_risk_scope
from sate_control.state import combined_reporting_state, group_state
from sate_control.security import CsrfGuard
from sate_factlog.log import FactLog

try:
    from sate_rcb.api import post_capital_ratify as rcb_post_capital_ratify
    from sate_rcb.service import RcbState
except ImportError:  # pragma: no cover - optional in minimal PYTHONPATH
    rcb_post_capital_ratify = None
    RcbState = None  # type: ignore[misc, assignment]


def _broker_gate(body: dict[str, object], log: FactLog | None = None):
    try:
        from sate_compliance.broker_ops_wire import gate_for_arm
        from sate_compliance.staging import complete_gate
    except ImportError:
        return None
    if bool(body.get("broker_verification_complete")):
        return complete_gate()
    as_of = str(body.get("as_of", "2026-10-23T00:00:00Z"))
    return gate_for_arm(log, as_of=as_of)


def _deliver_arm_otp(log: FactLog, *, otp: str, at: str) -> None:
    try:
        from sate_live_l1.telegram_otp import deliver_arm_otp
    except ImportError:
        return
    deliver_arm_otp(log, otp=otp, at=at)


def _activate_live_l1(log: FactLog, *, at: str, body: dict[str, object]) -> dict[str, object]:
    try:
        from sate_live_l1.transition import activate_live_l1
    except ImportError:
        return {}
    session_id = str(body.get("first_session_id", f"live-l1-{at[:10]}"))
    return activate_live_l1(
        log,
        at=at,
        first_session_id=session_id,
        flat_confirmed=body.get("flat_confirmed") is True,
    )


def _live_readiness(body: dict[str, object], log: FactLog | None, *, broker_preflight_ok: bool):
    try:
        from sate_live_readiness.preflight_engine import assess_for_arm
    except ImportError:
        return None
    as_of = str(body.get("as_of", "2026-10-23T00:00:00Z"))
    return assess_for_arm(
        body,
        log=log,
        as_of=as_of,
        broker_preflight_ok=broker_preflight_ok,
    )


@dataclass
class ControlApi:
    log: FactLog
    session: Session
    arming: ArmingSession = field(default_factory=lambda: ArmingSession(scope="A"))
    now: str = "2026-10-23T00:00:00Z"
    _audit_seq: int = 0
    csrf: CsrfGuard = field(default_factory=lambda: CsrfGuard(secret=b"sate-control-api-phase17"))
    rcb_state: object | None = None

    def issue_csrf(self) -> dict[str, str]:
        return {"csrf_token": self.csrf.issue(self.session.principal)}

    def dispatch(
        self,
        method: str,
        path: str,
        body: dict[str, object],
        *,
        csrf_token: str | None = None,
    ) -> dict[str, object]:
        if method == "POST" and not self.csrf.validate(csrf_token, self.session.principal):
            raise PermissionError("csrf token invalid")
        if method == "GET" and path == "/state":
            return self.get_state(body)
        if method == "GET" and path == "/reporting/combined":
            return self.get_combined_reporting(body)
        handlers = {
            ("POST", "/kill"): self.post_kill,
            ("POST", "/mode/A/sim"): self.post_mode_sim,
            ("POST", "/mode/A/arm"): self.post_mode_arm,
            ("POST", "/mode/A/confirm"): self.post_mode_confirm,
            ("POST", "/mode/A/cancel"): self.post_mode_cancel,
            ("POST", "/resume/A"): self.post_resume,
            ("POST", "/checkin"): self.post_checkin,
            ("POST", "/checkin/away"): self.post_checkin_away,
            ("POST", "/capital/ratify"): self.post_capital_ratify,
        }
        handler = handlers.get((method, path))
        if handler is None:
            raise ValueError(f"unknown route {method} {path}")
        return handler(body)

    def get_state(self, body: dict[str, object]) -> dict[str, object]:
        scope = authorize_read(self.session, str(body.get("scope", "A")))
        return group_state(
            scope=scope,
            mode=str(body.get("mode", "SIM")),
            halt_level=str(body.get("halt_level", "")),
            kill_state=str(body.get("kill_state", "")),
            heartbeat_ok=bool(body.get("heartbeat_ok", True)),
            fingerprint=str(body.get("fingerprint", "fp-1")),
        )

    def get_combined_reporting(self, body: dict[str, object]) -> dict[str, object]:
        authorize_read(self.session, "A")
        return combined_reporting_state(
            a_equity=str(body.get("a_equity", "0")),
            b_equity=str(body.get("b_equity", "0")),
        )

    def post_kill(self, body: dict[str, object]) -> dict[str, object]:
        scope = str(body["scope"])
        if scope == "ALL":
            authorize_control(self.session, self.session.group_scope, allow_all_kill=True)
        else:
            authorize_control(self.session, scope)
        validated = validate_kill(
            scope=scope,
            kill_level=str(body["kill_level"]),
            channel=str(body.get("channel", "web")),
        )
        self._audit("kill", scope, str(body.get("detail", validated["kill_level"])))
        return validated

    def post_mode_sim(self, body: dict[str, object]) -> dict[str, object]:
        authorize_control(self.session, "A")
        require_passkey(assertion=_str(body, "passkey_assertion"), action="mode_sim")
        self._audit("mode_sim", "A", "LIVE-to-SIM")
        return {"scope": "A", "mode": "SIM"}

    def post_mode_arm(self, body: dict[str, object]) -> dict[str, object]:
        authorize_control(self.session, "A")
        reject_global_risk_scope(str(body.get("scope", "A")))
        broker_gate = _broker_gate(body, self.log)
        broker_ok = broker_gate is None or not broker_gate.block_reasons()  # type: ignore[union-attr]
        live_readiness = _live_readiness(body, self.log, broker_preflight_ok=broker_ok)
        preflight = preflight_arm_live(
            scope="A",
            clean_recon=bool(body.get("clean_recon", True)),
            constitution_pinned=bool(body.get("constitution_pinned", True)),
            mode=str(body.get("mode", "SIM")),
            arming_cancelled=bool(body.get("arming_cancelled", False)),
            broker_gate=broker_gate,
            live_readiness=live_readiness,
        )
        otp = str(body.get("otp", "123456"))
        result = self.arming.start_arm(
            passkey_assertion=_str(body, "passkey_assertion"),
            preflight=preflight,
            started_at=self.now,
            otp=otp,
        )
        if result.get("status") == "arming":
            _deliver_arm_otp(self.log, otp=otp, at=self.now)
        self._audit("arm_live", "A", result["status"])
        return result

    def post_mode_confirm(self, body: dict[str, object]) -> dict[str, object]:
        authorize_control(self.session, "A")
        skip_delay = bool(body.get("arming_delay_elapsed")) or bool(body.get("live_l1_staging"))
        result = self.arming.confirm(
            code=str(body["code"]),
            passkey_assertion=_str(body, "passkey_assertion"),
            now=self.now,
            skip_delay=skip_delay,
        )
        if result.get("mode") == "LIVE-L1":
            activation = _activate_live_l1(self.log, at=self.now, body=body)
            result = {**result, **activation}
        self._audit("confirm_live", "A", result.get("mode", ""))
        return result

    def post_mode_cancel(self, body: dict[str, object]) -> dict[str, object]:
        authorize_control(self.session, "A")
        result = self.arming.cancel()
        self._audit("cancel_arm", "A", result["status"])
        return result

    def post_resume(self, body: dict[str, object]) -> dict[str, object]:
        authorize_control(self.session, "A")
        validate_resume(str(body.get("channel", "web")))
        require_passkey(assertion=_str(body, "passkey_assertion"), action="resume")
        self._audit("resume", "A", "A")
        return {"scope": "A", "status": "resume_pending"}

    def post_checkin(self, body: dict[str, object]) -> dict[str, object]:
        authorize_control(self.session, "A")
        channel = str(body.get("channel", "web_passkey"))
        if channel == "web_passkey":
            require_passkey(assertion=_str(body, "passkey_assertion"), action="checkin")
        applied = apply_checkin(
            channel=channel,
            passkey_assertion=_optional_str(body, "passkey_assertion"),
        )
        self._audit("checkin", "A", channel)
        return applied

    def post_checkin_away(self, body: dict[str, object]) -> dict[str, object]:
        authorize_control(self.session, "A")
        applied = apply_away(
            channel="web_passkey",
            passkey_assertion=_str(body, "passkey_assertion"),
            days=int(body["days"]),
        )
        self._audit("checkin_away", "A", applied["away_days"])
        return applied

    def post_capital_ratify(self, body: dict[str, object]) -> dict[str, object]:
        authorize_control(self.session, "A")
        reject_global_risk_scope(str(body.get("scope", "A")))
        assertion = require_passkey(assertion=_str(body, "passkey_assertion"), action="ratify_rcb")
        if self.rcb_state is not None and rcb_post_capital_ratify is not None:
            self._audit_seq += 1
            correlation = f"web-ratify-{self._audit_seq}"
            self.rcb_state = rcb_post_capital_ratify(
                self.log,
                self.rcb_state,
                scope="A",
                passkey_assertion=assertion,
                now=self.now,
                event_id=correlation,
                recorded_at=self.now,
                correlation_id=correlation,
            )
            detail = str(getattr(self.rcb_state, "ratified_base", "ratified"))
        else:
            detail = "submitted"
        self._audit("ratify_rcb", "A", detail)
        return {"scope": "A", "status": "ratify_accepted", "detail": detail}

    def _audit(self, action: str, scope: str, detail: str) -> None:
        self._audit_seq += 1
        correlation = f"web-{action}-{self._audit_seq}"
        persist_owner_action(
            self.log,
            {
                "action": action,
                "scope": scope,
                "channel": "web",
                "principal": self.session.principal,
                "detail": detail,
            },
            event_id=correlation,
            occurred_at=self.now,
            recorded_at=self.now,
            correlation_id=correlation,
        )


def _str(body: dict[str, object], key: str) -> str:
    value = body.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required")
    return value.strip()


def _optional_str(body: dict[str, object], key: str) -> str | None:
    value = body.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value.strip() or None
