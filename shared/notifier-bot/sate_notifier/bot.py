"""notifier-bot update processor (**TG-PO-01**)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from sate_factlog.log import FactLog

from sate_notifier.alive import handle_alive
from sate_notifier.allowlist import Allowlist
from sate_notifier.away import away_menu
from sate_notifier.commands import classify_command, parse_command
from sate_notifier.delivery import DeliveryPolicy
from sate_notifier.fact_lookup import build_digest, explain_why
from sate_notifier.flows import begin_destructive, scope_tag
from sate_notifier.journal import log_telegram
from sate_notifier.keyboard import button_to_command
from sate_notifier.mute import apply_mute
from sate_notifier.replay import ReplayGuard
from sate_notifier.state_machine import StateStore
from sate_notifier.templates import format_outbound
from sate_notifier.templates_health import health_status
from sate_notifier.templates_treasury import treasury_card


@dataclass
class NotifierBot:
    log: FactLog
    allowlist: Allowlist
    replay: ReplayGuard = field(default_factory=ReplayGuard)
    delivery: DeliveryPolicy = field(default_factory=DeliveryPolicy)
    states: StateStore = field(default_factory=StateStore)
    now: str = "2026-10-23T00:00:00Z"

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
        command = parse_command(text) or button_to_command(text)
        if command == "/alive":
            alive = handle_alive(chat_allowed=True, user_allowed=True)
            self._log(message_id, user_id, "A", "CHECK-IN", "NOTICE", "alive")
            return {"status": "ok", "alive": alive}
        decision = classify_command(command)
        if decision["class"] == "abstain":
            self._log(message_id, user_id, "A", "MODE", "INFO", "web_only")
            return {"status": "abstain", "message": decision["message"]}
        if command in {"/halt", "/flatten", "/kill"}:
            action = command.lstrip("/")
            flow = begin_destructive(self.states.for_user(user_id), action)
            self._log(message_id, user_id, "A", "HALT", "WARN", f"begin_{action}")
            return {"status": "flow", "flow": flow, "scope_tag": scope_tag("A")}
        if command == "/mode a sim":
            flow = begin_destructive(self.states.for_user(user_id), "mode_sim")
            return {"status": "flow", "flow": flow}
        if command.startswith("/why"):
            parts = text.strip().split(maxsplit=1)
            ref = parts[1] if len(parts) > 1 else ""
            why = explain_why(self.log, ref)
            body = format_outbound(why["text"])
            self._log(message_id, user_id, "A", "SYSTEM", "INFO", "why")
            return {"status": "ok", "text": body, "fact_ref": why["fact_ref"]}
        if command == "/digest":
            digest = build_digest(self.log)
            body = format_outbound(digest["text"])
            self._log(message_id, user_id, "A", "SUMMARY", "INFO", "digest")
            return {"status": "ok", "text": body, "count": digest["count"]}
        if command.startswith("/mute"):
            muted = apply_mute(self.delivery, text, now=time.monotonic())
            self._log(message_id, user_id, "A", "SYSTEM", "INFO", "mute")
            return {"status": "ok", **muted}
        if command == "/away":
            menu = away_menu()
            self._log(message_id, user_id, "A", "CHECK-IN", "NOTICE", "away_web")
            return {"status": "abstain", **menu}
        if command == "/treasury":
            card = treasury_card(
                scope="A",
                cash_floor="500",
                obligations="0",
                reimbursement_state="none",
            )
            body = format_outbound(card["text"])
            self._log(message_id, user_id, "A", card["category"], card["severity"], "treasury")
            return {"status": "ok", "text": body}
        if command == "/health":
            card = health_status(scope="A", heartbeat_ok=True, feed_latency_ms="12")
            body = format_outbound(card["text"])
            self._log(message_id, user_id, "A", card["category"], card["severity"], "health")
            return {"status": "ok", "text": body}
        self._log(message_id, user_id, "A", "SYSTEM", "INFO", command or "text")
        return {"status": "ok", "command": command, "keyboard_persistent": True}

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
