"""Phase 18 reduce-only controls, batching, and honest cards."""

from __future__ import annotations

import os
import sqlite3
import unittest

from sate_control.auth import Session
from sate_control.router import ControlApi
from sate_factlog.log import FactLog

from sate_notifier.allowlist import Allowlist
from sate_notifier.bot import NotifierBot
from sate_notifier.delivery import DeliveryPolicy
from sate_notifier.polling import process_updates
from sate_notifier.runner import runtime_config
from sate_notifier.state_machine import BotState
from sate_notifier.tags import halt_line

_SECRET = b"phase18-confirm-secret"


def _log() -> FactLog:
    return FactLog(
        sqlite3.connect(":memory:"),
        writers=frozenset({"notifier-bot", "control-api"}),
        readers=frozenset({"notifier-bot", "control-api"}),
    )


def _bot(log: FactLog, **overrides: object) -> NotifierBot:
    options: dict[str, object] = {"unix_clock": lambda: 1_700_000_000}
    options.update(overrides)
    return NotifierBot(
        log=log,
        allowlist=Allowlist(chat_id="100", user_id="owner"),
        confirm_secret=_SECRET,
        reduce_dispatch=options.get("reduce_dispatch"),  # type: ignore[arg-type]
        unix_clock=options["unix_clock"],  # type: ignore[arg-type]
    )


def _say(bot: NotifierBot, update_id: int, text: str) -> dict[str, object]:
    return bot.handle_update(
        update_id=update_id,
        chat_id="100",
        user_id="owner",
        text=text,
        message_id=f"m-{update_id}",
    )


class Phase18ControlTests(unittest.TestCase):
    def test_halt_confirm_reaches_the_control_plane(self) -> None:
        log = _log()
        api = ControlApi(log=log, session=Session(principal="owner", group_scope="A"))
        bot = _bot(log, reduce_dispatch=api.telegram_reduce)
        started = _say(bot, 1, "/halt")
        self.assertEqual(started["status"], "flow")
        scoped = _say(bot, 2, "Group A")
        self.assertIn("A", str(scoped["confirm_label"]))
        done = _say(bot, 3, str(scoped["confirm_label"]))
        self.assertEqual(done["status"], "executed")
        nested = done["result"]
        self.assertIsInstance(nested, dict)
        self.assertEqual(nested["issued"], "true")
        self.assertEqual(api.kill_state, "K1")
        self.assertTrue(done["keyboard_persistent"])

    def test_k3_needs_two_presses_and_resume_never_dispatches(self) -> None:
        log = _log()
        calls: list[str] = []

        def dispatch(body: dict[str, object]) -> dict[str, object]:
            calls.append(str(body["action"]))
            return {"ok": "true"}

        bot = _bot(log, reduce_dispatch=dispatch)
        _say(bot, 1, "/kill")
        first = _say(bot, 2, "Group A")
        second = _say(bot, 3, str(first["token"]))
        self.assertEqual(second["status"], "await_second_confirm")
        self.assertIn("revokes credentials", str(second["confirm_label"]))
        self.assertEqual(calls, [])
        finished = _say(bot, 4, str(second["token"]))
        self.assertEqual(finished["status"], "executed")
        self.assertEqual(calls, ["kill"])
        result = finished["result"]
        self.assertIsInstance(result, dict)
        self.assertEqual(result["kill_level"], "K3")
        blocked = _say(bot, 5, "/resume")
        self.assertEqual(blocked["status"], "abstain")
        self.assertEqual(calls, ["kill"])

    def test_expired_confirm_resets(self) -> None:
        log = _log()
        clock = {"now": 1_700_000_000}
        bot = _bot(log, unix_clock=lambda: clock["now"])
        _say(bot, 1, "/flatten")
        _say(bot, 2, "Group A")
        clock["now"] += 31
        expired = _say(bot, 3, "Confirm flatten A")
        self.assertEqual(expired["reason"], "confirm token expired")
        self.assertEqual(bot.states.for_user("owner").state, BotState.READY)

    def test_group_flows_stay_independent(self) -> None:
        log = _log()
        bot = _bot(log)
        _say(bot, 1, "/halt")
        group_a = _say(bot, 2, "Group A")
        done_a = _say(bot, 3, str(group_a["token"]))
        result_a = done_a["result"]
        self.assertIsInstance(result_a, dict)
        self.assertEqual(result_a["scope"], "A")
        _say(bot, 4, "/halt")
        group_b = _say(bot, 5, "Group B")
        done_b = _say(bot, 6, str(group_b["token"]))
        result_b = done_b["result"]
        self.assertIsInstance(result_b, dict)
        self.assertEqual(result_b["scope"], "B")
        self.assertEqual(result_b["issued"], "false")

    def test_telegram_can_switch_to_sim_and_cannot_skip_the_web_passkey(self) -> None:
        log = _log()
        api = ControlApi(log=log, session=Session(principal="owner", group_scope="A"))
        api.mode = "LIVE-L1"
        bot = _bot(log, reduce_dispatch=api.telegram_reduce)
        _say(bot, 1, "/mode a sim")
        switched = _say(bot, 2, "Switch A to SIM")
        self.assertEqual(switched["status"], "executed")
        self.assertEqual(api.mode, "SIM")
        with self.assertRaises(ValueError):
            api.post_mode_sim({})

    def test_group_b_kill_does_not_land_on_the_group_a_plane(self) -> None:
        log = _log()
        api = ControlApi(log=log, session=Session(principal="owner", group_scope="A"))
        bot = _bot(log, reduce_dispatch=api.telegram_reduce)
        _say(bot, 1, "/halt")
        scoped = _say(bot, 2, "Group B")
        refused = _say(bot, 3, str(scoped["token"]))
        self.assertEqual(refused["status"], "error")
        self.assertEqual(api.kill_state, "")

    def test_cards_do_not_invent_figures_or_sum_groups(self) -> None:
        log = _log()
        bot = _bot(log)
        bot.note_desk(equity_a="10", equity_b="25", partial_halt=True, halt_command="HALT_CONFIRMED_ALL")
        health = _say(bot, 1, "/health")
        treasury = _say(bot, 2, "/treasury")
        pnl = _say(bot, 3, "/pnl")
        self.assertIn("unknown", str(health["text"]))
        self.assertNotIn("12", str(health["text"]))
        self.assertNotIn("500", str(treasury["text"]))
        self.assertNotIn("35", str(pnl["text"]))
        self.assertIn("Combined reporting", str(pnl["text"]))
        self.assertNotIn("HALT_CONFIRMED_ALL", halt_line("HALT_CONFIRMED_ALL", partial_halt=True))
        status = _say(bot, 4, "/status")
        self.assertNotIn("HALT_CONFIRMED_ALL", str(status["text"]))

    def test_live_info_waits_for_a_batch_threshold_and_critical_does_not(self) -> None:
        unset = DeliveryPolicy(live=True)
        self.assertFalse(unset.should_deliver("INFO", now=1.0, text="one"))
        self.assertTrue(unset.should_deliver("CRITICAL", now=1.0, text="down"))
        half = DeliveryPolicy(live=True, info_batch_limit=20)
        self.assertFalse(half.should_deliver("INFO", now=1.0, text="two"))
        capped = DeliveryPolicy(info_batch_limit=20, info_window_sec=60)
        for index in range(20):
            self.assertTrue(capped.should_deliver("INFO", now=float(index), text=f"n{index}"))
        self.assertFalse(capped.should_deliver("INFO", now=20.0, text="n20"))
        self.assertIn("n20", capped.flush_batch())
        fresh = DeliveryPolicy(info_batch_limit=20, info_window_sec=60)
        self.assertTrue(fresh.should_deliver("INFO", now=1.0, text="same"))
        self.assertFalse(fresh.should_deliver("INFO", now=2.0, text="same"))

    def test_otp_has_no_confirm_button_and_stays_out_of_the_fact_log(self) -> None:
        log = _log()
        bot = _bot(log)
        notice = bot.render_otp("998877")
        self.assertEqual(notice["buttons"], [])
        self.assertIn("998877", str(notice["text"]))
        self.assertTrue(notice["web_entry_only"])
        rows = log.poll(after_seq=0, group_scope="A", reader_id="notifier-bot")
        blob = str(rows[-1].payload)
        self.assertNotIn("998877", blob)
        self.assertIn("otp_issued", blob)

    def test_callback_confirm_and_runner_refuses_a_default_allowlist(self) -> None:
        log = _log()
        bot = _bot(log)
        sent: list[dict[str, object]] = []
        offset = process_updates(
            bot,
            [
                {
                    "update_id": 7,
                    "callback_query": {
                        "id": "cb-1",
                        "data": "/halt",
                        "from": {"id": "owner"},
                        "message": {"message_id": 9, "chat": {"id": "100"}},
                    },
                }
            ],
            sender=sent.append,
        )
        self.assertEqual(offset, 8)
        self.assertEqual(sent[0]["status"], "flow")
        self.assertIn("reply_keyboard", sent[0])
        keys = (
            "SATE_TELEGRAM_BOT_TOKEN",
            "SATE_TELEGRAM_CHAT_ID",
            "SATE_TELEGRAM_USER_ID",
            "SATE_NOTIFIER_CONFIRM_SECRET",
        )
        saved = {key: os.environ.get(key) for key in keys}
        try:
            for key in keys:
                os.environ.pop(key, None)
            os.environ["SATE_TELEGRAM_BOT_TOKEN"] = "token"
            self.assertIsNone(runtime_config())
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


if __name__ == "__main__":
    unittest.main()
