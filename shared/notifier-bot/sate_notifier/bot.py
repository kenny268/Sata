"""notifier-bot update processor (**TG-PO-01**)."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

from sate_factlog.log import FactLog

from sate_notifier.alive import handle_alive
from sate_notifier.allowlist import Allowlist
from sate_notifier.away import away_menu
from sate_notifier.cards import otp_notice, pnl_card, positions_card, status_card
from sate_notifier.commands import classify_command, parse_command
from sate_notifier.confirm import ConfirmError
from sate_notifier.delivery import DeliveryPolicy
from sate_notifier.desk import DeskView
from sate_notifier.fact_lookup import build_digest, explain_why
from sate_notifier.flows import (
    accept_confirm,
    begin_cancel_arm,
    begin_destructive,
    begin_mode_sim,
    select_scope,
)
from sate_notifier.journal import log_telegram
from sate_notifier.keyboard import REPLY_KEYBOARD, button_to_command
from sate_notifier.mute import apply_mute
from sate_notifier.replay import ReplayGuard
from sate_notifier.state_machine import BotState, StateStore
from sate_notifier.tags import scope_tag
from sate_notifier.templates import format_outbound
from sate_notifier.templates_health import health_status
from sate_notifier.templates_treasury import treasury_card

Dispatch = Callable[[dict[str, object]], dict[str, object]]
_WEB_ONLY = "Open the web control plane with passkey to continue."


@dataclass
class NotifierBot:
    log: FactLog
    allowlist: Allowlist
    replay: ReplayGuard = field(default_factory=ReplayGuard)
    delivery: DeliveryPolicy = field(default_factory=DeliveryPolicy)
    states: StateStore = field(default_factory=StateStore)
    desk: DeskView = field(default_factory=DeskView)
    confirm_secret: bytes = b""
    reduce_dispatch: Dispatch | None = None
    unix_clock: Callable[[], int] | None = None
    now: str = "2026-10-23T00:00:00Z"

    def note_desk(self, **fields: object) -> None:
        for key, value in fields.items():
            if not hasattr(self.desk, key):
                raise ValueError(f"unknown desk field {key}")
            setattr(self.desk, key, value)
        self.delivery.live = self.desk.mode.upper().startswith("LIVE")

    def render_otp(self, code: str) -> dict[str, object]:
        notice = otp_notice(code=code, mode=self.desk.mode or "SIM")
        self._log("otp", "notifier-bot", "A", "MODE", "WARN", "otp_issued")
        return self._with_keyboard(notice)

    def handle_update(
        self,
        *,
        update_id: int,
        chat_id: str,
        user_id: str,
        text: str,
        message_id: str,
    ) -> dict[str, object]:
        if not self.allowlist.authorized(chat_id=chat_id, user_id=user_id):
            self._log(message_id, user_id, "A", "SYSTEM", "WARN", "auth.failed")
            return {"status": "discarded", "reason": "auth.failed"}
        if not self.replay.accept(update_id):
            return {"status": "discarded", "reason": "replay"}
        pending = self._continue(user_id, text, message_id)
        if pending is not None:
            return pending
        command = self._command(text)
        if command == "/alive":
            alive = handle_alive(chat_allowed=True, user_allowed=True)
            control = self._dispatch({"action": "alive", "channel": "telegram", "scope": "A"})
            self._log(message_id, user_id, "A", "CHECK-IN", "NOTICE", "alive")
            return self._with_keyboard({"status": "ok", "alive": alive, "control": control})
        decision = classify_command(parse_command(command))
        if decision["class"] == "abstain":
            self._log(message_id, user_id, "A", "MODE", "INFO", "web_only")
            return self._with_keyboard({"status": "abstain", "message": decision["message"]})
        if command in {"/halt", "/flatten", "/kill"}:
            action = command.lstrip("/")
            flow = begin_destructive(self.states.for_user(user_id), action, now=self._unix())
            self._log(message_id, user_id, "A", "HALT", "WARN", f"begin_{action}")
            return self._with_keyboard({"status": "flow", "flow": flow, "scope_tag": scope_tag("A", self.desk.mode)})
        if command == "/mode a sim":
            return self._open_mode(user_id, message_id)
        if command == "/mode a cancel":
            return self._open_cancel(user_id, message_id)
        if command.startswith("/why"):
            parts = text.strip().split(maxsplit=1)
            ref = parts[1] if len(parts) > 1 else ""
            why = explain_why(self.log, ref, mode=self.desk.mode)
            body = format_outbound(why["text"])
            self._log(message_id, user_id, "A", "SYSTEM", "INFO", "why")
            return self._with_keyboard({"status": "ok", "text": body, "fact_ref": why["fact_ref"]})
        if command == "/digest":
            digest = build_digest(self.log, mode=self.desk.mode)
            body = format_outbound(digest["text"])
            self._log(message_id, user_id, "A", "SUMMARY", "INFO", "digest")
            return self._with_keyboard({"status": "ok", "text": body, "count": digest["count"]})
        if command == "/mute":
            muted = apply_mute(self.delivery, text, now=time.monotonic())
            self._log(message_id, user_id, "A", "SYSTEM", "INFO", "mute")
            return self._with_keyboard({"status": "ok", **muted})
        if command in {"/mask on", "/mask off"}:
            self.desk.mask_amounts = command.endswith("on")
            self._log(message_id, user_id, "A", "SYSTEM", "INFO", "mask")
            state = "on" if self.desk.mask_amounts else "off"
            return self._with_keyboard({"status": "ok", "mask": state})
        if command == "/away":
            menu = away_menu()
            self._log(message_id, user_id, "A", "CHECK-IN", "NOTICE", "away_web")
            return self._with_keyboard({"status": "abstain", **menu})
        if command == "/treasury":
            return self._read(message_id, user_id, "TREASURY", "NOTICE", self._treasury_text(), "treasury")
        if command == "/health":
            return self._read(message_id, user_id, "HEALTH", "INFO", self._health_text(), "health")
        if command == "/status":
            return self._read(message_id, user_id, "SYSTEM", "INFO", status_card(self.desk), "status")
        if command == "/positions":
            return self._read(message_id, user_id, "TRADE", "INFO", positions_card(self.desk), "positions")
        if command == "/pnl":
            return self._read(message_id, user_id, "SUMMARY", "INFO", pnl_card(self.desk), "pnl")
        if command == "/help":
            return self._read(message_id, user_id, "SYSTEM", "INFO", _WEB_ONLY, "help")
        if command == "/controls":
            menu = "Halt, Flatten, Kill, Mode to SIM, Check-in, Away, Cancel arming. Resume and LIVE stay on the web."
            return self._read(message_id, user_id, "SYSTEM", "INFO", menu, "controls")
        self._log(message_id, user_id, "A", "SYSTEM", "INFO", command or "text")
        return self._with_keyboard({"status": "ok", "command": command})

    def _continue(self, user_id: str, text: str, message_id: str) -> dict[str, object] | None:
        session = self.states.for_user(user_id)
        if session.state == BotState.READY:
            return None
        moment = self._unix()
        if session.expires_at and moment > session.expires_at:
            session.reset()
            self._log(message_id, user_id, "A", "HALT", "WARN", "confirm_expired")
            return self._with_keyboard({"status": "error", "reason": "confirm token expired"})
        if text.strip().lower() == "cancel":
            session.reset()
            self._log(message_id, user_id, "A", "HALT", "INFO", "cancelled")
            return self._with_keyboard({"status": "cancelled"})
        if text.strip().startswith("/"):
            session.reset()
            return None
        try:
            if session.state == BotState.AWAITING_SCOPE:
                count = "unknown"
                if self.desk.positions_loaded:
                    count = str(len(self.desk.positions))
                flow = select_scope(
                    session,
                    text,
                    secret=self.confirm_secret,
                    now=moment,
                    position_count=count,
                )
                scope_name = str(flow.get("scope", "A"))
                self._log(message_id, user_id, _fact_scope(scope_name), "HALT", "WARN", "scope")
                return self._with_keyboard({"status": "flow", **flow})
            if session.state in {BotState.AWAITING_CONFIRM, BotState.AWAITING_KILL2}:
                scope_name = session.pending_scope or "A"
                token = _token_for(session, text)
                flow = accept_confirm(
                    session,
                    token,
                    secret=self.confirm_secret,
                    now=moment,
                    dispatch=self.reduce_dispatch,
                )
                self._log(message_id, user_id, _fact_scope(scope_name), "HALT", "WARN", str(flow["status"]))
                return self._with_keyboard({"status": "flow", **flow})
        except ConfirmError as exc:
            self.states.for_user(user_id).reset()
            self._log(message_id, user_id, "A", "HALT", "WARN", "confirm_error")
            return self._with_keyboard({"status": "error", "reason": str(exc)})
        except ValueError as exc:
            self.states.for_user(user_id).reset()
            self._log(message_id, user_id, "A", "HALT", "WARN", "confirm_error")
            return self._with_keyboard({"status": "error", "reason": str(exc)})
        return None

    def _open_mode(self, user_id: str, message_id: str) -> dict[str, object]:
        try:
            flow = begin_mode_sim(self.states.for_user(user_id), secret=self.confirm_secret, now=self._unix())
        except ConfirmError as exc:
            return self._with_keyboard({"status": "error", "reason": str(exc)})
        self._log(message_id, user_id, "A", "MODE", "WARN", "begin_mode_sim")
        return self._with_keyboard({"status": "flow", "flow": flow})

    def _open_cancel(self, user_id: str, message_id: str) -> dict[str, object]:
        try:
            flow = begin_cancel_arm(
                self.states.for_user(user_id), secret=self.confirm_secret, now=self._unix()
            )
        except ConfirmError as exc:
            return self._with_keyboard({"status": "error", "reason": str(exc)})
        self._log(message_id, user_id, "A", "MODE", "WARN", "begin_cancel_arm")
        return self._with_keyboard({"status": "flow", "flow": flow})

    def _read(
        self,
        message_id: str,
        user_id: str,
        category: str,
        severity: str,
        text: str,
        event: str,
    ) -> dict[str, object]:
        body = format_outbound(text)
        self._log(message_id, user_id, "A", category, severity, event)
        return self._with_keyboard({"status": "ok", "text": body})

    def _treasury_text(self) -> str:
        card = treasury_card(
            scope="A",
            mode=self.desk.mode,
            cash_floor=self.desk.cash_floor,
            obligations=self.desk.obligations,
            reimbursement_state=self.desk.reimbursement_state,
        )
        return card["text"]

    def _health_text(self) -> str:
        card = health_status(
            scope="A",
            mode=self.desk.mode,
            heartbeat_ok=self.desk.heartbeat_ok,
            feed_latency_ms=self.desk.feed_latency_ms,
        )
        return card["text"]

    def _dispatch(self, body: dict[str, object]) -> dict[str, object] | None:
        if self.reduce_dispatch is None:
            return None
        return self.reduce_dispatch(body)

    def _command(self, text: str) -> str:
        normalized = " ".join(text.strip().lower().split())
        if normalized.startswith("/mode") or normalized.startswith("/mask") or normalized.startswith("/why"):
            return normalized.split("@", 1)[0]
        return parse_command(text) or button_to_command(text)

    def _unix(self) -> int:
        if self.unix_clock is None:
            return int(time.time())
        return int(self.unix_clock())

    def _with_keyboard(self, payload: dict[str, object]) -> dict[str, object]:
        payload["reply_keyboard"] = REPLY_KEYBOARD
        payload["keyboard_persistent"] = True
        return payload

    def _log(
        self,
        message_id: str,
        principal: str,
        scope: str,
        category: str,
        severity: str,
        resulting_event: str,
    ) -> None:
        if not self.delivery.should_deliver(severity, category=category):
            resulting_event = f"suppressed:{resulting_event}"
        correlation = f"tg-{message_id}"
        log_telegram(
            self.log,
            message_id=message_id,
            principal=principal,
            scope=scope,
            category=category,
            severity=severity,
            resulting_event=resulting_event,
            event_id=correlation,
            occurred_at=self.now,
            recorded_at=self.now,
            correlation_id=correlation,
        )


def _fact_scope(scope: str) -> str:
    if scope == "ALL":
        return "GLOBAL"
    if scope in {"A", "B"}:
        return scope
    return "A"


def _token_for(session: object, text: str) -> str:
    cleaned = text.strip()
    label = getattr(session, "pending_label", "")
    issued = getattr(session, "issued_token", "")
    alt_label = getattr(session, "alt_label", "")
    alt = getattr(session, "alt_token", "")
    if cleaned == label and issued:
        return str(issued)
    if cleaned == alt_label and alt:
        return str(alt)
    return cleaned
