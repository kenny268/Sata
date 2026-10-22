import inspect
import json
import os
import sqlite3
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from sate_capital.ledger import blank as capital_blank
from sate_capital.ledger import effective_limit_base
from sate_capital.sourced import replay as capital_replay
from sate_factlog.log import FactLog

from sate_rcb.api import post_capital_ratify
from sate_rcb.bootstrap import main, matches_replay
from sate_rcb.errors import RcbError
from sate_rcb.service import (
    blank,
    effective_limit,
    floor_met,
    verdict_inputs,
)
from sate_rcb.sourced import (
    replay,
    submit_bind,
    submit_deposit,
    submit_halt,
    submit_halt_clear,
    submit_propose,
    submit_ratify,
    submit_withdrawal,
)


def _log() -> FactLog:
    parties = frozenset({"rcb", "capital", "kernel-a", "control-api"})
    return FactLog(sqlite3.connect(":memory:"), writers=parties)


class _Ids:
    def __init__(self) -> None:
        self._n = 0

    def __call__(self, when: str = "2026-10-01T00:00:00Z") -> dict[str, str]:
        self._n += 1
        return {
            "event_id": f"r-{self._n}",
            "occurred_at": when,
            "recorded_at": when,
            "correlation_id": "rcb-1",
        }


def _cash(scope: str = "A", withdrawable: str = "80") -> object:
    return replace(
        capital_blank(scope),
        currency="USD",
        withdrawable=withdrawable,
    )


class RcbTests(unittest.TestCase):
    def test_bind_requires_a_passkey_and_sets_version(self) -> None:
        state = blank("A")
        with self.assertRaises(RcbError):
            submit_bind(_log(), state, "100", passkey_assertion="  ", **_Ids()())
        bound = submit_bind(_log(), state, "100", passkey_assertion="owner-passkey", **_Ids()())
        self.assertEqual(bound.ratified_base, "100")
        self.assertEqual(bound.version, 1)
        self.assertEqual(verdict_inputs(bound, "100")["rcb_version"], 1)

    def test_ratify_waits_fourteen_clean_days(self) -> None:
        ids = _Ids()
        log = _log()
        state = submit_bind(log, blank("A"), "100", passkey_assertion="owner-passkey", **ids())
        state = submit_propose(log, state, "180", **ids("2026-10-01T00:00:00Z"))
        self.assertEqual(effective_limit(state, "180"), "100")
        self.assertEqual(state.ratified_base, "100")
        with self.assertRaises(RcbError) as caught:
            submit_ratify(
                log,
                state,
                passkey_assertion="owner-passkey",
                ratified_at="2026-10-14T00:00:00Z",
                event_id="early",
                recorded_at="2026-10-14T00:00:00Z",
                correlation_id="rcb-1",
            )
        self.assertEqual(caught.exception.code, "cool_off_incomplete")
        self.assertEqual(replay(log, "A").ratified_base, "100")
        ratified = post_capital_ratify(
            log,
            state,
            scope="A",
            passkey_assertion="owner-passkey",
            now="2026-10-15T00:00:00Z",
            event_id="on-time",
            recorded_at="2026-10-15T00:00:00Z",
            correlation_id="rcb-1",
        )
        self.assertEqual(ratified.ratified_base, "180")
        self.assertEqual(ratified.version, 2)
        self.assertIsNone(ratified.proposed_base)
        inputs = verdict_inputs(ratified, "180")
        self.assertEqual(inputs["effective_limit"], "180")
        self.assertEqual(inputs["rcb_version"], 2)

    def test_missing_passkey_keeps_the_existing_base(self) -> None:
        ids = _Ids()
        log = _log()
        state = submit_bind(log, blank("A"), "100", passkey_assertion="owner-passkey", **ids())
        state = submit_propose(log, state, "180", **ids("2026-10-01T00:00:00Z"))
        with self.assertRaises(RcbError) as caught:
            post_capital_ratify(
                log,
                state,
                scope="A",
                passkey_assertion="",
                now="2026-10-20T00:00:00Z",
                event_id="no-key",
                recorded_at="2026-10-20T00:00:00Z",
                correlation_id="rcb-1",
            )
        self.assertEqual(caught.exception.code, "passkey_required")
        self.assertEqual(replay(log, "A").ratified_base, "100")
        self.assertEqual(effective_limit(replay(log, "A"), "250"), "100")

    def test_severe_halt_restarts_the_cool_off(self) -> None:
        ids = _Ids()
        log = _log()
        state = submit_bind(log, blank("A"), "100", passkey_assertion="owner-passkey", **ids())
        state = submit_propose(log, state, "150", **ids("2026-10-01T00:00:00Z"))
        state = submit_halt(log, state, "L2", **ids("2026-10-10T00:00:00Z"))
        self.assertEqual(state.clean_since, "2026-10-10T00:00:00Z")
        self.assertTrue(state.injections_paused)
        with self.assertRaises(RcbError):
            submit_ratify(
                log,
                state,
                passkey_assertion="owner-passkey",
                ratified_at="2026-10-15T00:00:00Z",
                event_id="during",
                recorded_at="2026-10-15T00:00:00Z",
                correlation_id="rcb-1",
            )
        state = submit_halt_clear(log, state, **ids("2026-10-16T00:00:00Z"))
        with self.assertRaises(RcbError):
            submit_ratify(
                log,
                state,
                passkey_assertion="owner-passkey",
                ratified_at="2026-10-20T00:00:00Z",
                event_id="too-soon",
                recorded_at="2026-10-20T00:00:00Z",
                correlation_id="rcb-1",
            )
        ratified = submit_ratify(
            log,
            state,
            passkey_assertion="owner-passkey",
            ratified_at="2026-10-24T00:00:00Z",
            event_id="after-restart",
            recorded_at="2026-10-24T00:00:00Z",
            correlation_id="rcb-1",
        )
        self.assertEqual(ratified.ratified_base, "150")

    def test_level_one_does_not_restart_the_clock(self) -> None:
        ids = _Ids()
        log = _log()
        state = submit_bind(log, blank("A"), "100", passkey_assertion="owner-passkey", **ids())
        state = submit_propose(log, state, "150", **ids("2026-10-01T00:00:00Z"))
        state = submit_halt(log, state, "L1", **ids("2026-10-10T00:00:00Z"))
        self.assertEqual(state.clean_since, "2026-10-01T00:00:00Z")
        self.assertFalse(state.injections_paused)
        state = submit_halt_clear(log, state, **ids("2026-10-11T00:00:00Z"))
        ratified = submit_ratify(
            log,
            state,
            passkey_assertion="owner-passkey",
            ratified_at="2026-10-15T00:00:00Z",
            event_id="after-l1",
            recorded_at="2026-10-15T00:00:00Z",
            correlation_id="rcb-1",
        )
        self.assertEqual(ratified.ratified_base, "150")

    def test_deposit_during_halt_is_inert(self) -> None:
        ids = _Ids()
        log = _log()
        state = submit_bind(log, blank("A"), "100", passkey_assertion="owner-passkey", **ids())
        state = submit_halt(log, state, "L2", **ids("2026-10-02T00:00:00Z"))
        state = submit_deposit(log, state, "50", **ids("2026-10-03T00:00:00Z"))
        self.assertIsNone(state.proposed_base)
        self.assertEqual(state.ratified_base, "100")
        self.assertEqual(state.last_deposit_effect, "inert_halt")
        state = submit_halt_clear(log, state, **ids("2026-10-04T00:00:00Z"))
        state = submit_deposit(log, state, "50", **ids("2026-10-04T00:00:00Z"))
        self.assertEqual(state.proposed_base, "150")
        self.assertEqual(state.ratified_base, "100")
        self.assertEqual(state.clean_since, "2026-10-02T00:00:00Z")

    def test_equity_below_the_base_shrinks_the_limit(self) -> None:
        state = submit_bind(
            _log(), blank("A"), "100", passkey_assertion="owner-passkey", **_Ids()()
        )
        self.assertEqual(effective_limit(state, "40"), "40")
        self.assertEqual(state.version, 1)

    def test_floor_uses_the_ratified_base(self) -> None:
        low = submit_bind(
            _log(), blank("A"), "400", passkey_assertion="owner-passkey", **_Ids()()
        )
        self.assertFalse(floor_met(low))
        self.assertEqual(effective_limit(low, "2000"), "400")
        met = submit_bind(
            _log(), blank("A"), "500", passkey_assertion="owner-passkey", **_Ids()()
        )
        self.assertTrue(floor_met(met))
        self.assertEqual(effective_limit(met, "100"), "100")

    def test_withdrawal_reduces_the_base_when_cash_allows(self) -> None:
        ids = _Ids()
        log = _log()
        state = submit_bind(log, blank("A"), "100", passkey_assertion="owner-passkey", **ids())
        reduced = submit_withdrawal(
            log,
            state,
            _cash(withdrawable="80"),
            {"amount": "30", "fee": "1", "fx_cost": "0", "currency": "USD"},
            **ids(),
        )
        self.assertEqual(reduced.ratified_base, "70")
        self.assertEqual(reduced.version, 2)
        with self.assertRaises(RcbError):
            submit_withdrawal(
                log,
                reduced,
                _cash(withdrawable="10"),
                {"amount": "20", "fee": "0", "fx_cost": "0", "currency": "USD"},
                **ids(),
            )
        self.assertEqual(replay(log, "A").ratified_base, "70")
        with self.assertRaises(RcbError):
            submit_withdrawal(
                log,
                reduced,
                _cash(scope="B", withdrawable="1000"),
                {"amount": "10", "fee": "0", "fx_cost": "0", "currency": "USD"},
                **ids(),
            )

    def test_other_group_and_pooled_keys_do_not_raise_the_base(self) -> None:
        ids = _Ids()
        log = _log()
        bound = submit_bind(
            log, blank("B"), "80", passkey_assertion="owner-passkey", **ids()
        )
        self.assertEqual(replay(log, "A").version, 0)
        self.assertEqual(bound.ratified_base, "80")
        self.assertEqual(replay(log, "B").ratified_base, "80")

    def test_combined_key_is_rejected(self) -> None:
        log = _log()
        log.append(
            event_id="pooled",
            event_type="rcb_change",
            group_scope="A",
            occurred_at="2026-10-01T00:00:00Z",
            recorded_at="2026-10-01T00:00:00Z",
            correlation_id="rcb-1",
            writer_id="rcb",
            payload={"kind": "bind", "ratified_base": "10", "combined_rcb": "99"},
        )
        with self.assertRaises(RcbError):
            replay(log, "A")

    def test_a_short_cool_off_in_the_log_does_not_apply(self) -> None:
        ids = _Ids()
        log = _log()
        state = submit_bind(log, blank("A"), "100", passkey_assertion="owner-passkey", **ids())
        state = submit_propose(log, state, "140", **ids("2026-10-01T00:00:00Z"))
        log.append(
            event_id="forged",
            event_type="rcb_change",
            group_scope="A",
            occurred_at="2026-10-02T00:00:00Z",
            recorded_at="2026-10-02T00:00:00Z",
            correlation_id="rcb-1",
            writer_id="rcb",
            payload={
                "kind": "ratify",
                "passkey_assertion": "owner-passkey",
                "ratified_at": "2026-10-02T00:00:00Z",
                "clean_since": state.clean_since,
                "previous_base": "100",
                "new_base": "140",
            },
        )
        with self.assertRaises(RcbError):
            replay(log, "A")

    def test_a_halt_fact_restarts_the_cool_off(self) -> None:
        ids = _Ids()
        log = _log()
        state = submit_bind(log, blank("A"), "100", passkey_assertion="owner-passkey", **ids())
        log.append(
            event_id="halt-l3",
            event_type="halt",
            group_scope="A",
            occurred_at="2026-10-08T00:00:00Z",
            recorded_at="2026-10-08T00:00:00Z",
            correlation_id="halt-1",
            writer_id="kernel-a",
            payload={"level": "L3"},
        )
        state = replay(log, "A")
        self.assertEqual(state.clean_since, "2026-10-08T00:00:00Z")
        self.assertTrue(state.injections_paused)
        self.assertEqual(state.ratified_base, "100")
        state = submit_deposit(log, state, "25", **ids("2026-10-09T00:00:00Z"))
        self.assertIsNone(state.proposed_base)
        self.assertEqual(state.last_deposit_effect, "inert_halt")
        with self.assertRaises(RcbError) as caught:
            submit_ratify(
                log,
                state,
                passkey_assertion="owner-passkey",
                ratified_at="2026-10-20T00:00:00Z",
                event_id="while-paused",
                recorded_at="2026-10-20T00:00:00Z",
                correlation_id="rcb-1",
            )
        self.assertEqual(caught.exception.code, "injections_paused")

    def test_another_writer_cannot_change_the_base(self) -> None:
        log = _log()
        log.append(
            event_id="admin-bind",
            event_type="rcb_change",
            group_scope="A",
            occurred_at="2026-10-01T00:00:00Z",
            recorded_at="2026-10-01T00:00:00Z",
            correlation_id="rcb-1",
            writer_id="control-api",
            payload={
                "kind": "bind",
                "ratified_base": "900",
                "passkey_assertion": "owner-passkey",
            },
        )
        with self.assertRaises(RcbError) as caught:
            replay(log, "A")
        self.assertEqual(caught.exception.code, "writer")

    def test_kernel_projection_follows_the_ratified_base(self) -> None:
        ids = _Ids()
        log = _log()
        state = submit_bind(log, blank("A"), "100", passkey_assertion="owner-passkey", **ids())
        state = submit_propose(log, state, "180", **ids("2026-10-01T00:00:00Z"))
        state = submit_ratify(
            log,
            state,
            passkey_assertion="owner-passkey",
            ratified_at="2026-10-15T00:00:00Z",
            event_id="kernel",
            recorded_at="2026-10-15T00:00:00Z",
            correlation_id="rcb-1",
        )
        capital = capital_replay(log, "A")
        self.assertEqual(capital.ratified_base, "180")
        self.assertEqual(
            verdict_inputs(state, capital.equity)["effective_limit"],
            effective_limit_base(capital),
        )
        self.assertEqual(
            verdict_inputs(state, "90"),
            {"group_scope": "A", "rcb_version": 2, "effective_limit": "90"},
        )

    def test_replay_matches_and_a_tampered_projection_does_not(self) -> None:
        ids = _Ids()
        log = _log()
        submit_bind(log, blank("A"), "100", passkey_assertion="owner-passkey", **ids())
        with self.assertRaises(RcbError):
            verdict_inputs(blank("A"), "100")
        with TemporaryStore(log) as database:
            self.assertTrue(matches_replay(database, log, "A"))
            connection = sqlite3.connect(database)
            connection.execute(
                "UPDATE projection SET payload_json = ? WHERE id = 1",
                (json.dumps({"version": 9}),),
            )
            connection.commit()
            connection.close()
            self.assertFalse(matches_replay(database, log, "A"))

    def test_bootstrap_prints_the_version(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            fact = root / "fact.db"
            projection = root / "rcb.db"
            log = FactLog(sqlite3.connect(fact), writers=frozenset({"rcb"}))
            submit_bind(
                log, blank("A"), "100", passkey_assertion="owner-passkey", **_Ids()()
            )
            os.environ["SATE_GROUP_SCOPE"] = "A"
            os.environ["SATE_FACTLOG_DB"] = str(fact)
            os.environ["SATE_RCB_DB"] = str(projection)
            main()
            opened = FactLog(sqlite3.connect(fact), writers=frozenset({"rcb"}))
            self.assertTrue(matches_replay(projection, opened, "A"))

    def test_ratify_has_no_default_passkey(self) -> None:
        signature = inspect.signature(submit_ratify)
        self.assertIs(signature.parameters["passkey_assertion"].default, inspect.Parameter.empty)
        self.assertFalse(hasattr(submit_ratify, "increase_rcb"))


class TemporaryStore:
    def __init__(self, log: FactLog) -> None:
        self._log = log
        self._dir = None

    def __enter__(self) -> Path:
        from tempfile import TemporaryDirectory

        self._dir = TemporaryDirectory()
        database = Path(self._dir.name) / "rcb.db"
        os.environ["SATE_GROUP_SCOPE"] = "A"
        os.environ["SATE_FACTLOG_DB"] = ":memory:"
        # The in-memory log cannot be reopened. Store from the live projection.
        from sate_rcb.bootstrap import _store
        from sate_rcb.service import export_state

        _store(database, export_state(replay(self._log, "A")))
        return database

    def __exit__(self, *_) -> None:
        if self._dir is not None:
            self._dir.cleanup()


if __name__ == "__main__":
    unittest.main()
