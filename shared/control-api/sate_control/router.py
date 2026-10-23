"""control-api route dispatcher (**§13.2**)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from sate_control.arming import ArmingSession
from sate_control.audit import persist_owner_action
from sate_control.auth import Session, authorize_control, authorize_read
from sate_control.checkin_service import apply_away, apply_checkin
from sate_control.kill import validate_kill, validate_resume
from sate_halt.c1_runbook import KillView, run_c1
from sate_control.passkey import require_passkey
from sate_control.preflight import preflight_arm_live
from sate_control.reporting import reject_global_risk_scope
from sate_control.dashboard import (
    blank_performance,
    clean_position,
    eligibility_view,
    health_view,
    journal_view,
    performance_view,
    positions_view,
    treasury_view,
)
from sate_control.state import attention_flags, combined_reporting_state, group_state, unknown_capital
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
    mode: str = "SIM"
    halt_level: str = ""
    kill_state: str = ""
    fingerprint: str = "fp-1"
    heartbeat_ok: bool = True
    trading_revoked: bool = False
    partial_halt: bool = False
    halt_command: str = ""
    exposure: str = "unknown"
    margin: str = "unknown"
    distance_to_limits: str = "unknown"
    broker_health: str = "unknown"
    report_b_equity: str = ""
    kill_command_id: str = ""
    _capital_loaded: bool = False
    _capital: dict[str, str] = field(default_factory=unknown_capital)
    _constitution: dict[str, object] | None = None
    _coordinator: object | None = None
    _positions_loaded: bool = False
    _positions: list[dict[str, str]] = field(default_factory=list)
    _performance: dict[str, dict[str, str]] = field(
        default_factory=lambda: {"SIM": blank_performance(), "LIVE": blank_performance()}
    )
    _treasury_loaded: bool = False
    _cash_floor: str = "unknown"
    _reimbursement_owed: str = "unknown"
    _treasury_cases: list[object] = field(default_factory=list)
    _withdrawals: list[object] = field(default_factory=list)
    _notifications: list[str] = field(default_factory=list)
    _audit_seq: int = 0
    csrf: CsrfGuard = field(default_factory=lambda: CsrfGuard(secret=b"sate-control-api-phase17"))
    rcb_state: object | None = None

    def issue_csrf(self) -> dict[str, str]:
        return {"csrf_token": self.csrf.issue(self.session.principal)}

    def note_capital_book(self, book: dict[str, object]) -> None:
        cleaned = unknown_capital()
        for key in cleaned:
            value = book.get(key, "unknown")
            if not isinstance(value, str):
                raise ValueError(f"{key} must be a decimal string")
            cleaned[key] = value
        self._capital = cleaned
        self._capital_loaded = True

    def note_reporting_equity(self, scope: str, equity: str) -> None:
        if scope != "B":
            raise ValueError("Group A equity comes from the capital book")
        if not isinstance(equity, str):
            raise ValueError("equity must be a decimal string")
        self.report_b_equity = equity

    def note_constitution(self, view: dict[str, object]) -> None:
        if view.get("read_only") is not True:
            raise ValueError("constitution view is read-only")
        self._constitution = dict(view)

    def note_positions(self, rows: list[dict[str, object]]) -> None:
        self._positions = [clean_position(row) for row in rows]
        self._positions_loaded = True

    def note_performance(self, mode: str, book: dict[str, object]) -> None:
        if mode not in {"SIM", "LIVE"}:
            raise ValueError("performance books stay separate for SIM and LIVE")
        cleaned = blank_performance()
        for key in cleaned:
            value = book.get(key, "unknown")
            if not isinstance(value, str):
                raise ValueError(f"{key} must be a string")
            cleaned[key] = value
        self._performance[mode] = cleaned

    def note_risk(self, *, exposure: str, margin: str, distance_to_limits: str) -> None:
        self.exposure = _money_or_unknown(exposure)
        self.margin = _money_or_unknown(margin)
        self.distance_to_limits = _money_or_unknown(distance_to_limits)

    def note_treasury(self, view: dict[str, object]) -> None:
        cash_floor = view.get("cash_floor", "unknown")
        owed = view.get("reimbursement_owed", "unknown")
        cases = view.get("cases", [])
        withdrawals = view.get("withdrawals", [])
        if not isinstance(cash_floor, str) or not isinstance(owed, str):
            raise ValueError("treasury amounts must be strings")
        if not isinstance(cases, list) or not isinstance(withdrawals, list):
            raise ValueError("treasury cases must be lists")
        self._cash_floor = cash_floor
        self._reimbursement_owed = owed
        self._treasury_cases = list(cases)
        self._withdrawals = list(withdrawals)
        self._treasury_loaded = True

    def note_notification(self, text: str) -> None:
        if not text:
            raise ValueError("notification text is required")
        self._notifications.append(text)

    def dispatch(
        self,
        method: str,
        path: str,
        body: dict[str, object],
        *,
        csrf_token: str | None = None,
    ) -> dict[str, object]:
        if self.session.expires_at and self.session.expires_at <= self.now:
            raise PermissionError("session expired")
        if method == "POST" and not self.csrf.validate(csrf_token, self.session.principal):
            raise PermissionError("csrf token invalid")
        if method == "GET" and path == "/state":
            return self.get_state(body)
        if method == "GET" and path == "/reporting/combined":
            return self.get_combined_reporting(body)
        if method == "GET" and path == "/constitution":
            return self.get_constitution(body)
        if method == "GET" and path == "/positions":
            return self.get_positions(body)
        if method == "GET" and path == "/performance":
            return self.get_performance(body)
        if method == "GET" and path == "/eligibility":
            return self.get_eligibility(body)
        if method == "GET" and path == "/journal":
            return self.get_journal(body)
        if method == "GET" and path == "/treasury":
            return self.get_treasury(body)
        if method == "GET" and path == "/health":
            return self.get_health(body)
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
        constitution = self._constitution or {}
        pending = constitution.get("pending")
        pending_count = len(pending) if isinstance(pending, list) else 0
        time_lock = _time_lock(constitution) if self._constitution is not None else "unset"
        return group_state(
            scope=scope,
            mode=self.mode,
            halt_level=self.halt_level,
            kill_state=self.kill_state,
            heartbeat_ok=self.heartbeat_ok,
            fingerprint=self.fingerprint,
            capital=self._capital,
            attention=attention_flags(
                capital_loaded=self._capital_loaded,
                heartbeat_ok=self.heartbeat_ok,
                halt_level=self.halt_level,
                kill_state=self.kill_state,
                trading_revoked=self.trading_revoked,
                constitution_loaded=self._constitution is not None,
                session_expires_at=self.session.expires_at,
                arming_phase=self.arming.phase,
            ),
            trading_revoked=self.trading_revoked,
            partial_halt=self.partial_halt,
            halt_command=self.halt_command,
            exposure=self.exposure,
            margin=self.margin,
            distance_to_limits=self.distance_to_limits,
            arming_phase=self.arming.phase,
            arming_reasons=list(self.arming.pending_reasons),
            constitution_loaded=self._constitution is not None,
            active_version=constitution.get("active_version"),
            pending_count=pending_count,
            time_lock=time_lock,
        )

    def get_combined_reporting(self, body: dict[str, object]) -> dict[str, object]:
        del body
        authorize_read(self.session, "A")
        return combined_reporting_state(
            a_equity=self._capital["equity"] if self._capital_loaded else "unknown",
            b_equity=self.report_b_equity or "unknown",
        )

    def get_constitution(self, body: dict[str, object]) -> dict[str, object]:
        authorize_read(self.session, str(body.get("scope", "A")))
        if self._constitution is None:
            return {
                "read_only": True,
                "active_version": None,
                "pending": [],
                "time_lock": "unset",
                "live_blockers": ["constitution_unloaded"],
            }
        payload = dict(self._constitution)
        payload["read_only"] = True
        payload["time_lock"] = _time_lock(self._constitution)
        return payload

    def get_positions(self, body: dict[str, object]) -> dict[str, object]:
        scope = authorize_read(self.session, str(body.get("scope", "A")))
        return positions_view(scope=scope, loaded=self._positions_loaded, rows=self._positions)

    def get_performance(self, body: dict[str, object]) -> dict[str, object]:
        scope = authorize_read(self.session, str(body.get("scope", "A")))
        return performance_view(scope=scope, books=self._performance)

    def get_eligibility(self, body: dict[str, object]) -> dict[str, object]:
        scope = authorize_read(self.session, str(body.get("scope", "A")))
        blockers: list[str] = []
        if self._constitution is None:
            blockers.append("constitution_unloaded")
        else:
            raw = self._constitution.get("live_blockers", [])
            if isinstance(raw, list):
                blockers.extend(str(item) for item in raw)
        return eligibility_view(
            scope=scope,
            constitution_blockers=blockers,
            arming_reasons=list(self.arming.pending_reasons),
        )

    def get_journal(self, body: dict[str, object]) -> dict[str, object]:
        scope = authorize_read(self.session, str(body.get("scope", "A")))
        entries: list[dict[str, object]] = []
        try:
            rows = self.log.poll(after_seq=0, group_scope=scope, reader_id="control-api")
        except (PermissionError, ValueError):
            rows = []
        for row in rows:
            payload = row.payload if isinstance(row.payload, dict) else {}
            why = payload.get("detail", payload.get("action", ""))
            entries.append(
                {
                    "seq": row.seq,
                    "event_type": row.event_type,
                    "occurred_at": row.occurred_at,
                    "why": str(why),
                }
            )
        return journal_view(scope=scope, entries=entries)

    def get_treasury(self, body: dict[str, object]) -> dict[str, object]:
        scope = authorize_read(self.session, str(body.get("scope", "A")))
        if not self._treasury_loaded:
            return treasury_view(
                scope=scope,
                cash_floor="unknown",
                reimbursement_owed="unknown",
                cases=[],
                withdrawals=[],
            )
        return treasury_view(
            scope=scope,
            cash_floor=self._cash_floor,
            reimbursement_owed=self._reimbursement_owed,
            cases=self._treasury_cases,
            withdrawals=self._withdrawals,
        )

    def get_health(self, body: dict[str, object]) -> dict[str, object]:
        scope = authorize_read(self.session, str(body.get("scope", "A")))
        chain = "unknown"
        replay_events = 0
        try:
            broken = self.log.verify(reader_id="control-api")
            chain = "intact" if broken is None else "broken"
            replay_events = len(
                self.log.replay_through(
                    group_scope=scope,
                    as_of=self.now,
                    reader_id="control-api",
                )
            )
        except (PermissionError, ValueError):
            chain = "unknown"
        return health_view(
            scope=scope,
            heartbeat_ok=self.heartbeat_ok,
            broker=self.broker_health,
            hash_chain=chain,
            replay_events=replay_events,
            notifications=list(self._notifications),
        )

    def ack_kernel(self, command_id: str) -> str:
        if self._coordinator is None or not command_id:
            raise ValueError("no halt command is open")
        state = self._coordinator.ack_a(command_id)  # type: ignore[attr-defined]
        self.halt_command = str(state.value)
        if self.halt_command == "HALT_CONFIRMED_ALL":
            self.partial_halt = False
        self._audit("kernel_ack", "A", self.halt_command)
        return self.halt_command

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
        if self.kill_state == "K3":
            raise ValueError("kill sealed")
        level = validated["kill_level"]
        self.kill_state = level
        if level == "K3":
            self.trading_revoked = True
        command_id = f"web-kill-{self._audit_seq + 1}"
        self.kill_command_id = command_id
        halt_state = self._issue_kill(command_id, scope, level, validated["channel"])
        self.halt_command = halt_state
        self.partial_halt = scope == "ALL" and halt_state != "HALT_CONFIRMED_ALL"
        self._audit("kill", scope, f"{level}:{command_id}")
        return {**validated, "command_id": command_id, "halt_state": halt_state}

    def post_mode_sim(self, body: dict[str, object]) -> dict[str, object]:
        authorize_control(self.session, "A")
        require_passkey(assertion=_str(body, "passkey_assertion"), action="mode_sim")
        self.mode = "SIM"
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
            self.mode = "LIVE-L1"
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
        minutes = body.get("resume_cooloff_minutes")
        cool_off = minutes if isinstance(minutes, int) and minutes > 0 else None
        kill_level = str(body.get("kill_level") or self.kill_state)
        result = run_c1(
            KillView(
                channel="web",
                kill_level=kill_level,
                broker_positions=_labels(body, "broker_positions"),
                system_positions=_labels(body, "system_positions"),
                fact_logged=body.get("fact_logged") is True or self.kill_state == kill_level,
                web_passkey=True,
                recon_clean=body.get("recon_clean") is True,
                reprovisioned=body.get("reprovisioned") is True,
                sim_before_live=body.get("sim_before_live") is True,
                cool_off_minutes=cool_off,
                cool_off_elapsed=body.get("cool_off_elapsed") is True,
                preflight_passed=body.get("preflight_passed") is True,
                halt_level=str(body.get("halt_level", "")),
                killed_on=str(body.get("killed_on", "")),
                resume_on=str(body.get("resume_on", "")),
            )
        )
        status = "resume_allowed" if result.resume_allowed else "resume_blocked"
        self._audit("resume", "A", status)
        return {"scope": "A", "status": status, "steps": result.steps}

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

    def _issue_kill(self, command_id: str, scope: str, level: str, channel: str) -> str:
        try:
            from sate_halt.service import Coordinator
        except ImportError:
            return "kernel_command_unissued"
        if self._coordinator is None:
            self._coordinator = Coordinator()
        command = self._coordinator.issue(  # type: ignore[attr-defined]
            command_id=command_id,
            scope=scope,
            kill_level=level,
            reason="owner",
            channel=channel,
            identity=self.session.principal,
            b_reachable=False,
        )
        return str(command.status().value)

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


def _money_or_unknown(value: str) -> str:
    if value == "unknown":
        return value
    try:
        Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("risk figure must be a decimal string or unknown") from exc
    return value


def _time_lock(view: dict[str, object]) -> str:
    explicit = view.get("time_lock")
    if isinstance(explicit, str) and explicit:
        return explicit
    pending = view.get("pending")
    if not isinstance(pending, list) or not pending:
        return "unset"
    states = [
        str(item.get("lock_state", "unset"))
        for item in pending
        if isinstance(item, dict)
    ]
    if "awaiting_owner_hours" in states:
        return "unset"
    if "locked" in states:
        return "locked"
    if "eligible" in states:
        return "eligible"
    return "unset"


def _str(body: dict[str, object], key: str) -> str:
    value = body.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required")
    return value.strip()


def _labels(body: dict[str, object], key: str) -> tuple[str, ...]:
    value = body.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return (f"malformed:{key}",)
    return tuple(value)


def _optional_str(body: dict[str, object], key: str) -> str | None:
    value = body.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value.strip() or None
