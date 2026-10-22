import json
import os
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from sate_factlog.log import FactLog

from sate_capital.bootstrap import main, matches_replay
from sate_capital.broker import mock_deposit
from sate_capital.errors import CapitalError
from sate_capital.ledger import blank, effective_limit_base, project, tie_out
from sate_capital.sourced import (
    replay,
    submit_adjustment,
    submit_bind,
    submit_deposit,
    submit_fill_fees,
    submit_obligation,
    submit_snapshot,
    submit_swap_accrual,
    submit_withdrawal,
)


def _log() -> FactLog:
    parties = frozenset({"capital", "kernel-a", "control-api"})
    return FactLog(sqlite3.connect(":memory:"), writers=parties)


class _Ids:
    def __init__(self) -> None:
        self._n = 0

    def __call__(self) -> dict[str, str]:
        self._n += 1
        return {
            "event_id": f"e-{self._n}",
            "occurred_at": "2026-10-22T00:00:00Z",
            "recorded_at": "2026-10-22T00:00:01Z",
            "correlation_id": "capital-1",
        }


def _snapshot(**overrides: str) -> dict[str, str]:
    payload = {
        "broker_id": "exness",
        "account_id": "1001",
        "currency": "USD",
        "source_ts": "2026-10-22T00:00:00Z",
        "equity": "1000",
        "realised_pnl": "40",
        "settled": "800",
        "reserved": "50",
        "cash_floor": "100",
    }
    payload.update(overrides)
    return payload


class CapitalLedgerTests(unittest.TestCase):
    def test_withdrawable_is_not_equity(self) -> None:
        state = submit_snapshot(_log(), blank("A"), _snapshot(), **_Ids()())
        self.assertEqual(state.equity, "1000")
        self.assertEqual(state.settled, "800")
        self.assertEqual(state.reserved, "50")
        self.assertEqual(state.withdrawable, "650")
        self.assertNotEqual(state.withdrawable, state.equity)
        self.assertTrue(tie_out(state)["withdrawable_matches_formula"])
        self.assertTrue(tie_out(state)["buckets_are_distinct_fields"])
        self.assertFalse(hasattr(state, "cash"))

    def test_snapshot_cannot_carry_a_cash_alias_or_raise_the_base(self) -> None:
        state = blank("A")
        with self.assertRaises(CapitalError):
            submit_snapshot(_log(), state, _snapshot(withdrawable="1000"), **_Ids()())
        with self.assertRaises(CapitalError):
            submit_snapshot(_log(), state, {**_snapshot(), "ratified_base": "9999"}, **_Ids()())

    def test_limits_use_the_lower_of_base_and_equity(self) -> None:
        ids = _Ids()
        log = _log()
        state = submit_snapshot(log, blank("A"), _snapshot(equity="700"), **ids())
        state = submit_bind(log, state, "500", **ids())
        self.assertEqual(effective_limit_base(state), "500")
        state = submit_snapshot(
            log, state, _snapshot(equity="400", source_ts="2026-10-22T01:00:00Z"), **ids()
        )
        self.assertEqual(state.ratified_base, "500")
        self.assertEqual(effective_limit_base(state), "400")

    def test_withdrawal_reduces_the_base_immediately(self) -> None:
        ids = _Ids()
        log = _log()
        state = submit_snapshot(log, blank("A"), _snapshot(cash_floor="0", reserved="0"), **ids())
        state = submit_bind(log, state, "800", **ids())
        state = submit_withdrawal(
            log,
            state,
            {"amount": "100", "fee": "2", "fx_cost": "0", "currency": "USD"},
            **ids(),
        )
        self.assertEqual(state.ratified_base, "700")
        self.assertEqual(state.withdrawal_fees, "2")
        self.assertEqual(state.withdrawal_fx, "0")
        self.assertEqual(state.withdrawable, "698")
        self.assertFalse(hasattr(type(state), "increase_rcb"))

    def test_withdrawal_above_withdrawable_is_rejected(self) -> None:
        ids = _Ids()
        log = _log()
        state = submit_snapshot(log, blank("A"), _snapshot(), **ids())
        state = submit_bind(log, state, "800", **ids())
        with self.assertRaises(CapitalError):
            submit_withdrawal(
                log,
                state,
                {"amount": "700", "fee": "0", "fx_cost": "0", "currency": "USD"},
                **ids(),
            )
        self.assertEqual(replay(log, "A").ratified_base, "800")

    def test_deposits_do_not_raise_the_ratified_base(self) -> None:
        ids = _Ids()
        log = _log()
        state = submit_snapshot(log, blank("A"), _snapshot(equity="500"), **ids())
        state = submit_bind(log, state, "500", **ids())
        state = submit_deposit(
            log, state, {"amount": "300", "currency": "USD", "halted": False}, **ids()
        )
        self.assertEqual(state.ratified_base, "500")
        self.assertEqual(state.last_deposit_effect, "inert_pending_ratification")
        state = submit_deposit(
            log, state, {"amount": "300", "currency": "USD", "halted": True}, **ids()
        )
        self.assertEqual(state.last_deposit_effect, "inert_halt")
        state = submit_snapshot(
            log, state, _snapshot(equity="800", source_ts="2026-10-22T01:00:00Z"), **ids()
        )
        self.assertEqual(state.ratified_base, "500")
        self.assertEqual(effective_limit_base(state), "500")
        with self.assertRaises(CapitalError):
            submit_bind(log, state, "800", **ids())

    def test_fill_records_costs_and_the_fx_rate(self) -> None:
        ids = _Ids()
        log = _log()
        state = submit_snapshot(log, blank("A"), _snapshot(), **ids())
        with self.assertRaises(CapitalError):
            submit_fill_fees(
                log,
                state,
                {
                    "fill_id": "f-1",
                    "currency": "USD",
                    "quote_currency": "USD",
                    "fx_rate": "1",
                    "commission": "3",
                    "slippage": "1",
                },
                **ids(),
            )
        state = submit_fill_fees(
            log,
            state,
            {
                "fill_id": "f-1",
                "currency": "USD",
                "quote_currency": "EUR",
                "fx_rate": "2",
                "commission": "3",
                "swap": "0",
                "slippage": "1",
            },
            **ids(),
        )
        self.assertEqual(state.trading_costs, "8")
        self.assertEqual(state.realised_pnl, "32")

    def test_other_group_obligation_does_not_become_cash(self) -> None:
        ids = _Ids()
        log = _log()
        state = submit_snapshot(log, blank("A"), _snapshot(), **ids())
        state = submit_obligation(
            log,
            state,
            {
                "obligation_id": "o-1",
                "owner": "owner",
                "due_date": "2026-11-01",
                "currency": "USD",
                "amount": "25",
                "broker_dependency": "other-broker",
                "funding_scope": "B",
                "reserve": True,
            },
            **ids(),
        )
        self.assertEqual(state.pending_obligations, "0")
        self.assertTrue(state.obligations[0].cross_broker_owner_transfer)
        self.assertEqual(state.withdrawable, "650")

    def test_reserved_obligation_lowers_withdrawable(self) -> None:
        ids = _Ids()
        log = _log()
        state = submit_snapshot(log, blank("A"), _snapshot(), **ids())
        state = submit_obligation(
            log,
            state,
            {
                "obligation_id": "o-1",
                "owner": "owner",
                "due_date": "2026-11-01",
                "currency": "USD",
                "amount": "25",
                "broker_dependency": "exness",
                "funding_scope": "A",
                "reserve": True,
            },
            **ids(),
        )
        self.assertEqual(state.pending_obligations, "25")
        self.assertEqual(state.withdrawable, "625")

    def test_adjustment_names_one_bucket(self) -> None:
        ids = _Ids()
        log = _log()
        state = submit_snapshot(log, blank("A"), _snapshot(), **ids())
        with self.assertRaises(CapitalError):
            submit_adjustment(
                log,
                state,
                {"bucket": "cash", "amount": "1", "currency": "USD", "principal": "owner"},
                **ids(),
            )
        state = submit_adjustment(
            log,
            state,
            {"bucket": "reserved", "amount": "80", "currency": "USD", "principal": "owner"},
            **ids(),
        )
        self.assertEqual(state.reserved, "80")
        self.assertEqual(state.withdrawable, "620")

    def test_replay_matches_the_incremental_projection(self) -> None:
        ids = _Ids()
        log = _log()
        state = submit_snapshot(log, blank("A"), _snapshot(), **ids())
        state = submit_bind(log, state, "500", **ids())
        rebuilt = replay(log, "A")
        self.assertEqual(rebuilt, state)
        records = log.poll(after_seq=0, group_scope="A", reader_id="capital")
        self.assertEqual(project("A", records), state)

    def test_other_scope_does_not_change_this_ledger(self) -> None:
        log = _log()
        log.append(
            event_id="e-b",
            event_type="broker_balances",
            group_scope="B",
            occurred_at="2026-10-22T00:00:00Z",
            recorded_at="2026-10-22T00:00:01Z",
            correlation_id="other",
            writer_id="kernel-a",
            payload={"kind": "snapshot", **_snapshot(equity="5"), "group_id": "B"},
        )
        self.assertEqual(replay(log, "A").equity, "0")

    def test_bootstrap_rebuilds_from_the_log(self) -> None:
        with TemporaryDirectory() as tmp:
            fact = Path(tmp) / "fact.db"
            projection = Path(tmp) / "capital.db"
            log = FactLog(sqlite3.connect(fact), writers=frozenset({"capital", "kernel-a"}))
            submit_snapshot(log, blank("A"), _snapshot(equity="420"), **_Ids()())
            os.environ["SATE_GROUP_SCOPE"] = "A"
            os.environ["SATE_FACTLOG_DB"] = str(fact)
            os.environ["SATE_CAPITAL_DB"] = str(projection)
            try:
                main()
                connection = sqlite3.connect(projection)
                row = connection.execute("SELECT payload_json FROM projection").fetchone()
                stored = json.loads(row[0])
                connection.close()
                self.assertEqual(stored["equity"], "420")
                self.assertEqual(stored["withdrawable"], "650")
            finally:
                os.environ.pop("SATE_GROUP_SCOPE", None)
                os.environ.pop("SATE_FACTLOG_DB", None)
                os.environ.pop("SATE_CAPITAL_DB", None)

    def test_snapshot_schema_keeps_the_buckets_separate(self) -> None:
        schema_path = (
            Path(__file__).resolve().parents[2] / "schemas" / "capital-snapshot.schema.json"
        )
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertNotIn("withdrawable", schema["properties"])
        self.assertIn("equity", schema["required"])
        self.assertIn("settled", schema["required"])

    def test_swap_accrual_is_explicit(self) -> None:
        ids = _Ids()
        log = _log()
        state = submit_snapshot(log, blank("A"), _snapshot(), **ids())
        state = submit_swap_accrual(
            log,
            state,
            {"accrual_id": "s-0", "amount": "0", "currency": "USD"},
            **ids(),
        )
        self.assertEqual(state.trading_costs, "0")
        state = submit_swap_accrual(
            log,
            state,
            {"accrual_id": "s-1", "amount": "1.5", "currency": "USD"},
            **ids(),
        )
        self.assertEqual(state.trading_costs, "1.5")
        self.assertEqual(state.realised_pnl, "38.5")

    def test_mock_broker_deposit_does_not_raise_the_base(self) -> None:
        ids = _Ids()
        log = _log()
        state = submit_snapshot(log, blank("A"), _snapshot(equity="500"), **ids())
        state = submit_bind(log, state, "500", **ids())
        stamp = {"occurred_at": "2026-10-22T02:00:00Z", "recorded_at": "2026-10-22T02:00:01Z"}
        state = mock_deposit(
            log,
            state,
            amount="300",
            halted=False,
            reported=_snapshot(equity="800", source_ts="2026-10-22T02:00:00Z"),
            event_id="ct-01",
            correlation_id="ct-01",
            **stamp,
        )
        self.assertEqual(state.equity, "800")
        self.assertEqual(state.ratified_base, "500")
        self.assertEqual(effective_limit_base(state), "500")
        self.assertEqual(state.last_deposit_effect, "inert_pending_ratification")
        state = mock_deposit(
            log,
            state,
            amount="50",
            halted=True,
            reported=_snapshot(equity="850", source_ts="2026-10-22T03:00:00Z"),
            event_id="ct-02",
            correlation_id="ct-02",
            occurred_at="2026-10-22T03:00:00Z",
            recorded_at="2026-10-22T03:00:01Z",
        )
        self.assertEqual(state.ratified_base, "500")
        self.assertEqual(state.last_deposit_effect, "inert_halt")

    def test_admin_adjustment_is_the_only_manual_write(self) -> None:
        ids = _Ids()
        log = _log()
        submit_snapshot(log, blank("A"), _snapshot(), **ids())
        log.append(
            event_id="e-bad",
            event_type="capital_state",
            group_scope="A",
            occurred_at="2026-10-22T04:00:00Z",
            recorded_at="2026-10-22T04:00:01Z",
            correlation_id="adj",
            writer_id="capital",
            payload={
                "kind": "adjustment",
                "bucket": "reserved",
                "amount": "1",
                "currency": "USD",
                "principal": "owner",
                "group_id": "A",
            },
        )
        with self.assertRaises(CapitalError):
            replay(log, "A")

    def test_a_tampered_projection_does_not_match_the_log(self) -> None:
        with TemporaryDirectory() as tmp:
            fact = Path(tmp) / "fact.db"
            projection = Path(tmp) / "capital.db"
            parties = frozenset({"capital", "kernel-a"})
            log = FactLog(sqlite3.connect(fact), writers=parties)
            submit_snapshot(log, blank("A"), _snapshot(), **_Ids()())
            os.environ["SATE_GROUP_SCOPE"] = "A"
            os.environ["SATE_FACTLOG_DB"] = str(fact)
            os.environ["SATE_CAPITAL_DB"] = str(projection)
            try:
                main()
                self.assertTrue(matches_replay(projection, log, "A"))
                connection = sqlite3.connect(projection)
                connection.execute(
                    "UPDATE projection SET payload_json = ?",
                    ('{"withdrawable": "equity"}',),
                )
                connection.commit()
                connection.close()
                self.assertFalse(matches_replay(projection, log, "A"))
                main()
                self.assertTrue(matches_replay(projection, log, "A"))
            finally:
                os.environ.pop("SATE_GROUP_SCOPE", None)
                os.environ.pop("SATE_FACTLOG_DB", None)
                os.environ.pop("SATE_CAPITAL_DB", None)


if __name__ == "__main__":
    unittest.main()
