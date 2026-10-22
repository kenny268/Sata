import json
import os
import sqlite3
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from sate_capital.ledger import CapitalState, blank as capital_blank
from sate_capital.sourced import replay as capital_replay
from sate_capital.sourced import submit_snapshot
from sate_factlog.log import FactLog

from sate_treasury.bootstrap import main, matches_replay
from sate_treasury.errors import TreasuryError
from sate_treasury.ledger import blank, dashboard, owed
from sate_treasury.sourced import (
    replay,
    submit_authorize,
    submit_cost,
    submit_obligation,
    submit_shared_cost,
    submit_transition,
)


def _log() -> FactLog:
    return FactLog(sqlite3.connect(":memory:"), writers=frozenset({"treasury"}))


class _Ids:
    def __init__(self) -> None:
        self._n = 0

    def __call__(self) -> dict[str, str]:
        self._n += 1
        return {
            "event_id": f"t-{self._n}",
            "occurred_at": "2026-10-22T00:00:00Z",
            "recorded_at": "2026-10-22T00:00:01Z",
            "correlation_id": "treasury-1",
        }


def _capital(scope: str = "A", withdrawable: str = "500") -> CapitalState:
    return CapitalState(
        group_scope=scope,
        currency="USD",
        broker_id="exness",
        account_id="1001",
        source_ts="2026-10-22T00:00:00Z",
        equity="500",
        realised_pnl="0",
        settled=withdrawable,
        reserved="0",
        withdrawable=withdrawable,
        ratified_base="500",
        cash_floor="0",
        pending_obligations="0",
        withdrawal_fees="0",
        withdrawal_fx="0",
        withdrawal_hold="0",
        trading_costs="0",
        last_deposit_effect="",
        obligations=(),
        last_seq=1,
    )


def _owner_cost(**extra: str) -> dict[str, object]:
    payload: dict[str, object] = {
        "cost_id": "c-1",
        "tag": "A",
        "path": "owner_paid",
        "amount": "40",
        "currency": "USD",
        "vendor": "host",
        "evidence": "inv-1",
        "reimbursement_id": "r-1",
    }
    payload.update(extra)
    return payload


class TreasuryTests(unittest.TestCase):
    def test_owner_paid_cost_does_not_enter_withdrawable(self) -> None:
        capital = _capital()
        state = submit_cost(_log(), blank(), _owner_cost(), **_Ids()())
        self.assertEqual(owed(state, "A"), "40")
        self.assertEqual(capital.withdrawable, "500")
        self.assertEqual(capital.ratified_base, "500")
        self.assertEqual(state.cases[0].status, "COST_RECORDED")
        self.assertFalse(state.cases[0].withdrawal_success)

    def test_broker_deducted_cost_creates_no_owed_balance(self) -> None:
        capital = _capital()
        payload = _owner_cost(path="broker_deducted")
        del payload["reimbursement_id"]
        state = submit_cost(_log(), blank(), payload, **_Ids()())
        self.assertEqual(owed(state, "A"), "0")
        self.assertEqual(state.cases, ())
        self.assertEqual(capital.withdrawable, "500")

    def test_reimbursed_only_after_a_matched_broker_movement(self) -> None:
        ids = _Ids()
        log = _log()
        capital = _capital()
        state = submit_cost(log, blank(), _owner_cost(), **ids())
        state = submit_transition(
            log,
            state,
            {"reimbursement_id": "r-1", "to_status": "REIMBURSEMENT_ELIGIBILITY_PENDING"},
            **ids(),
        )
        state = submit_authorize(log, state, "r-1", capital, **ids())
        self.assertEqual(state.cases[0].status, "REIMBURSEMENT_AUTHORIZED")
        self.assertFalse(state.cases[0].withdrawal_success)
        self.assertTrue(dashboard(state, "A")["cases"][0]["notice_due"])
        for status in ("WITHDRAWAL_PENDING_OWNER", "OWNER_CONFIRMED"):
            state = submit_transition(
                log,
                state,
                {"reimbursement_id": "r-1", "to_status": status},
                **ids(),
            )
            self.assertNotEqual(state.cases[0].status, "REIMBURSED")
        state = submit_transition(
            log,
            state,
            {
                "reimbursement_id": "r-1",
                "to_status": "BROKER_RECONCILIATION",
                "broker_movement_id": "m-1",
                "broker_matched": False,
            },
            **ids(),
        )
        with self.assertRaises(TreasuryError):
            submit_transition(
                log,
                state,
                {"reimbursement_id": "r-1", "to_status": "REIMBURSED"},
                **ids(),
            )
        self.assertEqual(owed(replay(log), "A"), "40")

    def test_matched_movement_closes_the_owed_amount(self) -> None:
        ids = _Ids()
        log = _log()
        state = self._to_owner_confirmed(log, ids)
        state = submit_transition(
            log,
            state,
            {
                "reimbursement_id": "r-1",
                "to_status": "BROKER_RECONCILIATION",
                "broker_movement_id": "m-1",
                "broker_matched": True,
            },
            **ids(),
        )
        state = submit_transition(
            log,
            state,
            {"reimbursement_id": "r-1", "to_status": "REIMBURSED"},
            **ids(),
        )
        self.assertTrue(state.cases[0].withdrawal_success)
        self.assertEqual(owed(state, "A"), "0")
        view = dashboard(state, "A")
        self.assertEqual(view["cases"][0]["status"], "REIMBURSED")
        self.assertTrue(view["read_only"])
        self.assertFalse(view["cases"][0]["notice_due"])

    def test_insufficient_cash_defers_without_authorising(self) -> None:
        ids = _Ids()
        log = _log()
        capital = _capital(withdrawable="10")
        state = submit_cost(log, blank(), _owner_cost(), **ids())
        state = submit_transition(
            log,
            state,
            {"reimbursement_id": "r-1", "to_status": "REIMBURSEMENT_ELIGIBILITY_PENDING"},
            **ids(),
        )
        state = submit_authorize(log, state, "r-1", capital, **ids())
        self.assertEqual(state.cases[0].status, "REIMBURSEMENT_ELIGIBILITY_PENDING")
        self.assertEqual(state.cases[0].defer_reason, "insufficient_withdrawable")
        self.assertFalse(state.cases[0].withdrawal_success)
        self.assertEqual(capital.withdrawable, "10")
        self.assertEqual(owed(state, "A"), "40")

    def test_amount_above_the_ratified_base_defers(self) -> None:
        ids = _Ids()
        log = _log()
        capital = _capital(withdrawable="500")
        capital = replace(capital, ratified_base="30")
        state = submit_cost(log, blank(), _owner_cost(), **ids())
        state = submit_transition(
            log,
            state,
            {"reimbursement_id": "r-1", "to_status": "REIMBURSEMENT_ELIGIBILITY_PENDING"},
            **ids(),
        )
        state = submit_authorize(log, state, "r-1", capital, **ids())
        self.assertEqual(state.cases[0].status, "REIMBURSEMENT_ELIGIBILITY_PENDING")
        self.assertEqual(state.cases[0].defer_reason, "above_ratified_base")
        self.assertEqual(owed(state, "A"), "40")

    def test_missed_deadline_keeps_the_owed_amount(self) -> None:
        ids = _Ids()
        log = _log()
        state = submit_cost(log, blank(), _owner_cost(), **ids())
        state = submit_transition(
            log,
            state,
            {"reimbursement_id": "r-1", "to_status": "REIMBURSEMENT_ELIGIBILITY_PENDING"},
            **ids(),
        )
        state = submit_authorize(log, state, "r-1", _capital(), **ids())
        state = submit_transition(
            log,
            state,
            {"reimbursement_id": "r-1", "to_status": "WITHDRAWAL_PENDING_OWNER"},
            **ids(),
        )
        state = submit_transition(
            log,
            state,
            {"reimbursement_id": "r-1", "to_status": "MISSED"},
            **ids(),
        )
        self.assertEqual(state.cases[0].status, "MISSED")
        self.assertEqual(owed(state, "A"), "40")
        self.assertFalse(state.cases[0].withdrawal_success)

    def test_cannot_skip_to_reimbursed(self) -> None:
        ids = _Ids()
        log = _log()
        state = submit_cost(log, blank(), _owner_cost(), **ids())
        with self.assertRaises(TreasuryError):
            submit_transition(
                log,
                state,
                {"reimbursement_id": "r-1", "to_status": "REIMBURSED"},
                **ids(),
            )
        self.assertEqual(replay(log).cases[0].status, "COST_RECORDED")

    def test_shared_cost_uses_caller_shares_and_does_not_move_capital(self) -> None:
        capital = _capital()
        state = submit_shared_cost(
            _log(),
            blank(),
            {
                "cost_id": "c-shared",
                "path": "owner_paid",
                "amount": "10",
                "currency": "USD",
                "vendor": "host",
                "evidence": "inv-9",
                "basis": "owner-supplied",
                "rule_version": "unratified",
                "shares": [
                    {"scope": "A", "amount": "4", "reimbursement_id": "r-a"},
                    {"scope": "B", "amount": "6", "reimbursement_id": "r-b"},
                ],
            },
            **_Ids()(),
        )
        self.assertEqual(owed(state, "A"), "4")
        self.assertEqual(owed(state, "B"), "6")
        self.assertEqual(state.allocations[0].basis, "owner-supplied")
        self.assertEqual(capital.ratified_base, "500")
        self.assertEqual(capital.withdrawable, "500")
        with self.assertRaises(TreasuryError):
            submit_shared_cost(
                _log(),
                blank(),
                {
                    "cost_id": "c-2",
                    "path": "owner_paid",
                    "amount": "10",
                    "currency": "USD",
                    "vendor": "host",
                    "evidence": "inv-2",
                    "basis": "",
                    "rule_version": "v",
                    "shares": [
                        {"scope": "A", "amount": "10", "reimbursement_id": "r-1"},
                        {"scope": "B", "amount": "0", "reimbursement_id": "r-2"},
                    ],
                },
                **_Ids()(),
            )

    def test_other_group_cost_does_not_increase_group_a_owed(self) -> None:
        payload = _owner_cost(tag="B", reimbursement_id="r-b")
        state = submit_cost(_log(), blank(), payload, **_Ids()())
        self.assertEqual(owed(state, "A"), "0")
        self.assertEqual(owed(state, "B"), "40")

    def test_obligation_is_tracked_without_changing_withdrawable(self) -> None:
        capital = _capital()
        state = submit_obligation(
            _log(),
            blank(),
            {
                "obligation_id": "o-1",
                "group_scope": "A",
                "owner": "owner",
                "due_date": "2026-11-01",
                "currency": "USD",
                "amount": "25",
                "broker_dependency": "exness",
                "reserve": True,
                "exposure_reduction_required": True,
            },
            **_Ids()(),
        )
        self.assertTrue(state.obligations[0].exposure_reduction_required)
        self.assertEqual(owed(state, "A"), "0")
        self.assertEqual(capital.withdrawable, "500")
        view = dashboard(state, "A")
        self.assertEqual(view["obligations"], ["o-1"])

    def test_replay_matches_the_submitted_projection(self) -> None:
        ids = _Ids()
        log = _log()
        state = submit_cost(log, blank(), _owner_cost(), **ids())
        self.assertEqual(replay(log), state)

    def test_bootstrap_shows_reimbursement_status(self) -> None:
        with TemporaryDirectory() as tmp:
            fact = Path(tmp) / "fact.db"
            projection = Path(tmp) / "treasury.db"
            log = FactLog(sqlite3.connect(fact), writers=frozenset({"treasury"}))
            submit_cost(log, blank(), _owner_cost(), **_Ids()())
            os.environ["SATE_GROUP_SCOPE"] = "A"
            os.environ["SATE_FACTLOG_DB"] = str(fact)
            os.environ["SATE_TREASURY_DB"] = str(projection)
            try:
                main()
                connection = sqlite3.connect(projection)
                row = connection.execute("SELECT payload_json FROM projection").fetchone()
                stored = json.loads(row[0])
                connection.close()
                self.assertEqual(stored["reimbursement_owed"], "40")
                self.assertEqual(stored["cases"][0]["status"], "COST_RECORDED")
                self.assertFalse(stored["cases"][0]["withdrawal_success"])
            finally:
                os.environ.pop("SATE_GROUP_SCOPE", None)
                os.environ.pop("SATE_FACTLOG_DB", None)
                os.environ.pop("SATE_TREASURY_DB", None)

    def test_owner_paid_cost_does_not_change_the_capital_projection(self) -> None:
        parties = frozenset({"treasury", "capital", "kernel-a"})
        log = FactLog(sqlite3.connect(":memory:"), writers=parties)
        ids = _Ids()
        submit_cost(log, blank(), _owner_cost(), **ids())
        self.assertEqual(capital_replay(log, "A").withdrawable, "0")
        self.assertEqual(owed(replay(log), "A"), "40")
        capital = submit_snapshot(
            log,
            capital_blank("A"),
            {
                "broker_id": "exness",
                "account_id": "1001",
                "currency": "USD",
                "source_ts": "2026-10-22T00:00:00Z",
                "equity": "500",
                "realised_pnl": "0",
                "settled": "500",
                "reserved": "0",
                "cash_floor": "0",
            },
            **ids(),
        )
        self.assertEqual(capital.withdrawable, "500")
        self.assertEqual(owed(replay(log), "A"), "40")

    def test_cost_event_cannot_carry_a_cash_field(self) -> None:
        payload = _owner_cost()
        payload["withdrawable"] = "40"
        with self.assertRaises(TreasuryError):
            submit_cost(_log(), blank(), payload, **_Ids()())

    def test_other_group_capital_cannot_authorise(self) -> None:
        ids = _Ids()
        log = _log()
        other = _capital(scope="B")
        state = submit_cost(log, blank(), _owner_cost(), **ids())
        state = submit_transition(
            log,
            state,
            {"reimbursement_id": "r-1", "to_status": "REIMBURSEMENT_ELIGIBILITY_PENDING"},
            **ids(),
        )
        with self.assertRaises(TreasuryError):
            submit_authorize(log, state, "r-1", other, **ids())
        self.assertEqual(replay(log).cases[0].status, "REIMBURSEMENT_ELIGIBILITY_PENDING")
        self.assertEqual(other.withdrawable, "500")

    def test_a_tampered_dashboard_does_not_match_the_log(self) -> None:
        with TemporaryDirectory() as tmp:
            fact = Path(tmp) / "fact.db"
            projection = Path(tmp) / "treasury.db"
            log = FactLog(sqlite3.connect(fact), writers=frozenset({"treasury"}))
            submit_cost(log, blank(), _owner_cost(), **_Ids()())
            os.environ["SATE_GROUP_SCOPE"] = "A"
            os.environ["SATE_FACTLOG_DB"] = str(fact)
            os.environ["SATE_TREASURY_DB"] = str(projection)
            try:
                main()
                self.assertTrue(matches_replay(projection, log, "A"))
                connection = sqlite3.connect(projection)
                connection.execute(
                    "UPDATE projection SET payload_json = ?",
                    ('{"withdrawal_success": true}',),
                )
                connection.commit()
                connection.close()
                self.assertFalse(matches_replay(projection, log, "A"))
                main()
                self.assertTrue(matches_replay(projection, log, "A"))
            finally:
                os.environ.pop("SATE_GROUP_SCOPE", None)
                os.environ.pop("SATE_FACTLOG_DB", None)
                os.environ.pop("SATE_TREASURY_DB", None)

    def _to_owner_confirmed(self, log: FactLog, ids: _Ids):
        state = submit_cost(log, blank(), _owner_cost(), **ids())
        for status in (
            "REIMBURSEMENT_ELIGIBILITY_PENDING",
            "REIMBURSEMENT_AUTHORIZED",
            "WITHDRAWAL_PENDING_OWNER",
            "OWNER_CONFIRMED",
        ):
            if status == "REIMBURSEMENT_AUTHORIZED":
                state = submit_authorize(log, state, "r-1", _capital(), **ids())
            else:
                state = submit_transition(
                    log,
                    state,
                    {"reimbursement_id": "r-1", "to_status": status},
                    **ids(),
                )
        return state


if __name__ == "__main__":
    unittest.main()
