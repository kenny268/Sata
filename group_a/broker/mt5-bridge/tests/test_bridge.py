"""Demo connect, fingerprint halt, and a reconnect that does not repeat an order."""

from __future__ import annotations

import pathlib
import threading
import unittest

from sate_mt5_bridge import (
    DEMO_SESSIONS,
    AdapterError,
    Bridge,
    MockTerminal,
    decode_frame,
    encode_frame,
    refuse_dealer,
)


def _terminal(
    *,
    login: str = "10001",
    server: str = "Exness-MT5Trial",
    mode: str = "SIM",
        fresh: bool = True,
        heartbeat_ok: bool = True,
        rate_limited: bool = False,
        settlement: str = "demo",
        equity: str = "",
        margin: str = "",
        currency: str = "",
        stop_attach_fails: bool = False,
    ) -> MockTerminal:
    return MockTerminal(
        login=login,
        server=server,
        mode=mode,
        bid="1.0850",
        ask="1.0852",
        server_time="2026-10-22T21:00:00Z",
        fresh=fresh,
        heartbeat_ok=heartbeat_ok,
        rate_limited=rate_limited,
        min_lot="1.25",
        lot_step="0.25",
        stops_level="8",
        settlement=settlement,
        equity=equity,
        margin=margin,
        currency=currency,
        stop_attach_fails=stop_attach_fails,
    )


def _grant() -> dict[str, object]:
    return {"group": "A", "injected": True}


_STOP = "1.0700"


def _open(bridge: Bridge, login: str = "10001") -> str:
    return bridge.connect(login, "Exness-MT5Trial", _grant(), instrument="EURUSD")


class BridgeTests(unittest.TestCase):
    def test_a_demo_session_subscribes_and_places_one_placeholder(self) -> None:
        terminal = _terminal()
        bridge = Bridge(terminal)
        self.assertEqual(_open(bridge), "HEALTHY")
        self.assertEqual(bridge.spec.min_lot, "1.25")
        self.assertEqual(bridge.quote["bid"], "1.0850")
        self.assertGreaterEqual(bridge.latency_us, 0)
        order = bridge.place_placeholder(
            verdict="Allow",
            idempotency_key="ord-1",
            instrument="EURUSD",
            side="BUY",
            quantity="1",
            reduce_only=False,
            protective_stop=_STOP,
        )
        self.assertEqual(order.state, "placeholder")
        self.assertTrue(order.stop_attached)
        self.assertEqual(order.protective_stop, _STOP)
        self.assertEqual(terminal.attached_stops, [_STOP])
        self.assertIsNone(order.broker_id)
        self.assertEqual(order.server_time, "2026-10-22T21:00:00Z")
        self.assertEqual(terminal.submits, ["ord-1"])
        again = bridge.place_placeholder(
            verdict="Allow",
            idempotency_key="ord-1",
            instrument="EURUSD",
            side="BUY",
            quantity="1",
            reduce_only=False,
            protective_stop=_STOP,
        )
        self.assertIs(again, order)
        self.assertEqual(terminal.submits, ["ord-1"])
        with self.assertRaises(AdapterError) as rejected:
            bridge.place_placeholder(
                verdict="Reject",
                idempotency_key="ord-2",
                instrument="EURUSD",
                side="BUY",
                quantity="1",
                reduce_only=False,
                protective_stop=_STOP,
            )
        self.assertEqual(rejected.exception.code, "verdict")
        bridge.close()

    def test_a_fingerprint_mismatch_halts_and_places_nothing(self) -> None:
        bridge = Bridge(_terminal())
        self.assertEqual(_open(bridge, "99999"), "UNVERIFIED")
        self.assertEqual(bridge.arm_halt, "L2")
        with self.assertRaises(AdapterError) as blocked:
            bridge.place_placeholder(
                verdict="Allow",
                idempotency_key="ord-1",
                instrument="EURUSD",
                side="BUY",
                quantity="1",
                reduce_only=False,
                protective_stop=_STOP,
            )
        self.assertEqual(blocked.exception.code, "state")
        self.assertEqual(bridge.terminal.submits, [])
        bridge.close()

    def test_reconnect_after_a_drop_does_not_repeat_the_order(self) -> None:
        terminal = _terminal()
        bridge = Bridge(terminal)
        _open(bridge)
        bridge.place_placeholder(
            verdict="AllowWithSize",
            idempotency_key="ord-1",
            instrument="EURUSD",
            side="SELL",
            quantity="1",
            reduce_only=False,
            protective_stop=_STOP,
        )
        bridge.crash()
        self.assertEqual(bridge.state, "UNAVAILABLE")
        self.assertEqual(bridge.completed_sessions, 0)
        with self.assertRaises(AdapterError) as dropped:
            _open(bridge)
        self.assertEqual(dropped.exception.code, "disconnect")
        self.assertEqual(bridge.state, "UNAVAILABLE")
        terminal.alive = True
        self.assertEqual(_open(bridge), "HEALTHY")
        self.assertEqual(terminal.submits, ["ord-1"])
        self.assertEqual(bridge.ghost_submits, 0)
        bridge.close()

    def test_a_stale_quote_and_an_unknown_settlement_block_the_placeholder(self) -> None:
        stale = Bridge(_terminal(fresh=False))
        self.assertEqual(_open(stale), "DEGRADED")
        with self.assertRaises(AdapterError) as blocked:
            stale.place_placeholder(
                verdict="Allow",
                idempotency_key="ord-1",
                instrument="EURUSD",
                side="BUY",
                quantity="1",
                reduce_only=False,
                protective_stop=_STOP,
            )
        self.assertEqual(blocked.exception.code, "state")
        stale.close()
        unknown = Bridge(_terminal(settlement="unknown"))
        self.assertEqual(_open(unknown), "HEALTHY")
        self.assertFalse(unknown.orders_enabled)
        with self.assertRaises(AdapterError) as settlement:
            unknown.place_placeholder(
                verdict="Allow",
                idempotency_key="ord-1",
                instrument="EURUSD",
                side="BUY",
                quantity="1",
                reduce_only=False,
                protective_stop=_STOP,
            )
        self.assertEqual(settlement.exception.code, "settlement")
        unknown.close()

    def test_the_sim_channel_refuses_a_live_account_and_a_password(self) -> None:
        bridge = Bridge(_terminal(mode="LIVE"))
        with self.assertRaises(AdapterError) as live:
            _open(bridge)
        self.assertEqual(live.exception.code, "live_on_sim")
        with self.assertRaises(AdapterError) as host:
            Bridge(_terminal(), channel="LIVE")
        self.assertEqual(host.exception.code, "host")
        leaked = {"group": "A", "injected": True, "password": "x"}
        with self.assertRaises(AdapterError) as password:
            bridge.connect("10001", "Exness-MT5Trial", leaked, instrument="EURUSD")
        self.assertEqual(password.exception.code, "credential")
        with self.assertRaises(AdapterError) as manual:
            bridge.withdraw()
        self.assertEqual(manual.exception.code, "manual")
        bridge.close()

    def test_five_mock_sessions_open_the_gate_and_a_fresh_bridge_does_not(self) -> None:
        fresh = Bridge(_terminal())
        self.assertFalse(fresh.gate_met())
        fresh.close()
        bridge = Bridge(_terminal())
        for _ in range(DEMO_SESSIONS - 1):
            _open(bridge)
            bridge.disconnect()
        self.assertFalse(bridge.gate_met())
        _open(bridge)
        bridge.disconnect()
        self.assertTrue(bridge.gate_met())
        bridge.channel = "LIVE"
        self.assertFalse(bridge.gate_met())
        bridge.close()

    def test_the_frame_is_the_socket_body_and_no_dealer_is_opened(self) -> None:
        frame = encode_frame("account", {"login": "10001"})
        self.assertEqual(decode_frame(frame)["op"], "account")
        with self.assertRaises(AdapterError) as dealer:
            refuse_dealer("tcp://127.0.0.1:5555")
        self.assertEqual(dealer.exception.code, "host")
        with self.assertRaises(AdapterError) as secret:
            encode_frame("account", {"password": "x"})
        self.assertEqual(secret.exception.code, "credential")

    def test_the_terminal_call_leaves_the_caller_thread(self) -> None:
        seen: list[str] = []

        class Spy(MockTerminal):
            def handle(self, op: str, payload: dict[str, object]) -> dict[str, object]:
                seen.append(threading.current_thread().name)
                return super().handle(op, payload)

        terminal = Spy(
            login="10001",
            server="Exness-MT5Trial",
            mode="SIM",
            bid="1.0850",
            ask="1.0852",
            server_time="2026-10-22T21:00:00Z",
        )
        bridge = Bridge(terminal)
        _open(bridge)
        self.assertTrue(seen)
        self.assertNotEqual(seen[0], threading.current_thread().name)
        self.assertTrue(seen[0].startswith("mt5-sync"))
        bridge.close()

    def test_poll_rechecks_the_fingerprint_and_a_stale_subscribe_degrades(self) -> None:
        terminal = _terminal()
        bridge = Bridge(terminal)
        self.assertEqual(_open(bridge), "HEALTHY")
        terminal.login = "10002"
        self.assertEqual(bridge.poll(), "UNVERIFIED")
        self.assertEqual(bridge.arm_halt, "L2")
        with self.assertRaises(AdapterError) as blocked:
            bridge.place_placeholder(
                verdict="Allow",
                idempotency_key="ord-2",
                instrument="EURUSD",
                side="BUY",
                quantity="1",
                reduce_only=False,
                protective_stop=_STOP,
            )
        self.assertEqual(blocked.exception.code, "state")
        terminal.login = "10001"
        self.assertEqual(bridge.poll(), "HEALTHY")
        self.assertIsNone(bridge.arm_halt)
        terminal.fresh = False
        quote = bridge.subscribe("EURUSD")
        self.assertEqual(quote["bid"], "1.0850")
        self.assertEqual(bridge.state, "DEGRADED")
        bridge.close()

    def test_reconnect_stays_reconciling_until_known_orders_match(self) -> None:
        terminal = _terminal()
        bridge = Bridge(terminal)
        _open(bridge)
        bridge.place_placeholder(
            verdict="Allow",
            idempotency_key="ord-1",
            instrument="EURUSD",
            side="BUY",
            quantity="1",
            reduce_only=False,
            protective_stop=_STOP,
        )
        bridge.crash()
        terminal.alive = True
        terminal.submits.append("extra")
        self.assertEqual(_open(bridge), "RECONCILING")
        with self.assertRaises(AdapterError) as blocked:
            bridge.place_placeholder(
                verdict="Allow",
                idempotency_key="ord-2",
                instrument="EURUSD",
                side="BUY",
                quantity="1",
                reduce_only=False,
                protective_stop=_STOP,
            )
        self.assertEqual(blocked.exception.code, "state")
        self.assertEqual(terminal.submits, ["ord-1", "extra"])
        bridge.disconnect()
        self.assertEqual(bridge.completed_sessions, 0)
        bridge.close()

    def test_a_missing_spec_blocks_risk_and_a_flatten_still_places(self) -> None:
        terminal = _terminal()
        terminal.min_lot = ""
        bridge = Bridge(terminal)
        self.assertEqual(_open(bridge), "HEALTHY")
        self.assertFalse(bridge.spec.complete)
        with self.assertRaises(AdapterError) as missing:
            bridge.place_placeholder(
                verdict="Allow",
                idempotency_key="ord-1",
                instrument="EURUSD",
                side="BUY",
                quantity="1",
                reduce_only=False,
                protective_stop=_STOP,
            )
        self.assertEqual(missing.exception.code, "spec")
        flatten = bridge.place_placeholder(
            verdict="Allow",
            idempotency_key="ord-flat",
            instrument="EURUSD",
            side="SELL",
            quantity="1",
            reduce_only=True,
        )
        self.assertEqual(flatten.state, "placeholder")
        self.assertEqual(terminal.submits, ["ord-flat"])
        bridge_source = pathlib.Path(__file__).parents[1] / "sate_mt5_bridge" / "bridge.py"
        self.assertNotIn("0.01", bridge_source.read_text())
        self.assertEqual(bridge.spec.min_lot, "")
        bridge.close()

    def test_reads_keep_decimal_strings_and_refuse_a_float(self) -> None:
        terminal = _terminal(equity="1000.00", margin="25.00", currency="USD")
        terminal.positions = [
            {
                "instrument": "EURUSD",
                "quantity": "1",
                "server_time": "2026-10-22T21:00:00Z",
            }
        ]
        terminal.fees = [
            {
                "amount": "0.30",
                "currency": "USD",
                "server_time": "2026-10-22T21:00:00Z",
            }
        ]
        bridge = Bridge(terminal)
        _open(bridge)
        self.assertEqual(bridge.balances()["equity"], "1000.00")
        self.assertEqual(bridge.positions()[0]["quantity"], "1")
        self.assertEqual(bridge.fills(), [])
        self.assertEqual(bridge.fees()[0]["amount"], "0.30")
        order = bridge.place_placeholder(
            verdict="Allow",
            idempotency_key="ord-1",
            instrument="EURUSD",
            side="BUY",
            quantity="1",
            reduce_only=False,
            protective_stop=_STOP,
        )
        self.assertIs(bridge.order_status("ord-1"), order)
        self.assertIsNone(bridge.order_status("ord-1").broker_id)
        with self.assertRaises(AdapterError) as amount:
            bridge.place_placeholder(
                verdict="Allow",
                idempotency_key="ord-2",
                instrument="EURUSD",
                side="BUY",
                quantity=1.0,
                reduce_only=False,
                protective_stop=_STOP,
            )
        self.assertEqual(amount.exception.code, "malformed")
        setattr(terminal, "equity", 10.0)
        with self.assertRaises(AdapterError) as floated:
            bridge.balances()
        self.assertEqual(floated.exception.code, "malformed")
        spaced = Bridge(_terminal(login="10 001"))
        self.assertEqual(
            spaced.connect("10 001", "Exness-MT5Trial", _grant(), instrument="EURUSD"),
            "UNVERIFIED",
        )
        self.assertEqual(spaced.arm_halt, "L2")
        quiet = Bridge(_terminal(heartbeat_ok=False))
        self.assertEqual(_open(quiet), "DEGRADED")
        limited = Bridge(_terminal(rate_limited=True))
        self.assertEqual(_open(limited), "DEGRADED")
        refused = Bridge(_terminal())
        with self.assertRaises(AdapterError) as injected:
            refused.connect(
                "10001",
                "Exness-MT5Trial",
                {"group": "A", "injected": False},
                instrument="EURUSD",
            )
        self.assertEqual(injected.exception.code, "credential")
        bridge.close()
        spaced.close()
        quiet.close()
        limited.close()
        refused.close()

    def test_bat_stop_attachment_is_verified_on_the_demo_terminal(self) -> None:
        terminal = _terminal()
        bridge = Bridge(terminal)
        _open(bridge)
        order = bridge.place_placeholder(
            verdict="Allow",
            idempotency_key="bat-1",
            instrument="EURUSD",
            side="BUY",
            quantity="1",
            reduce_only=False,
            protective_stop=_STOP,
        )
        self.assertTrue(order.stop_attached)
        self.assertEqual(terminal.attached_stops, [_STOP])
        bridge.close()

    def test_a_missing_stop_is_refused_before_the_terminal(self) -> None:
        bridge = Bridge(_terminal())
        _open(bridge)
        with self.assertRaises(AdapterError) as missing:
            bridge.place_placeholder(
                verdict="Allow",
                idempotency_key="ord-1",
                instrument="EURUSD",
                side="BUY",
                quantity="1",
                reduce_only=False,
            )
        self.assertEqual(missing.exception.code, "protective_stop")
        self.assertEqual(bridge.terminal.submits, [])
        bridge.close()

    def test_demo_risk_orders_never_submit_without_a_verified_stop(self) -> None:
        terminal = _terminal()
        bridge = Bridge(terminal)
        _open(bridge)
        for index in range(3):
            order = bridge.place_placeholder(
                verdict="Allow",
                idempotency_key=f"ord-{index}",
                instrument="EURUSD",
                side="BUY",
                quantity="1",
                reduce_only=False,
                protective_stop=_STOP,
            )
            self.assertTrue(order.stop_attached)
        self.assertEqual(len(terminal.submits), 3)
        self.assertEqual(len(terminal.attached_stops), 3)
        self.assertEqual(set(terminal.attached_stops), {_STOP})
        bridge.close()

    def test_a_broker_stop_failure_does_not_open(self) -> None:
        bridge = Bridge(_terminal(stop_attach_fails=True))
        _open(bridge)
        with self.assertRaises(AdapterError) as failed:
            bridge.place_placeholder(
                verdict="Allow",
                idempotency_key="ord-1",
                instrument="EURUSD",
                side="BUY",
                quantity="1",
                reduce_only=False,
                protective_stop=_STOP,
            )
        self.assertEqual(failed.exception.code, "protective_stop")
        self.assertEqual(bridge.terminal.submits, [])
        bridge.close()

    def test_monitor_exports_bridge_state(self) -> None:
        from sate_mt5_bridge.monitor import observation_from_bridge

        bridge = Bridge(_terminal(), channel="SIM")
        self.assertEqual(_open(bridge), "HEALTHY")
        obs = observation_from_bridge(bridge)
        self.assertEqual(obs["adapter_state"], "HEALTHY")
        self.assertEqual(obs["group_scope"], "A")
        bridge.close()


if __name__ == "__main__":
    unittest.main()
