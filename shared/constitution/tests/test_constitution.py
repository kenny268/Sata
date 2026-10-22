import copy
import inspect
import json
import os
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from sate_factlog.log import FactLog

from sate_constitution.bootstrap import main, matches_replay
from sate_constitution.document import live_blockers
from sate_constitution.errors import ConstitutionError
from sate_constitution.service import blank, trade_gate, view
from sate_constitution.signing import generate_keypair, seal
from sate_constitution.sourced import replay, submit_activate, submit_emergency, submit_propose

_ROOT = Path(__file__).resolve().parents[1]
_NOW = "2026-10-22T00:00:00Z"
_EFFECTIVE = "2026-01-01T00:00:00Z"
_EXPIRES = "2027-10-22T00:00:00Z"


def _log() -> FactLog:
    return FactLog(sqlite3.connect(":memory:"), writers=frozenset({"constitution"}))


class _Ids:
    def __init__(self) -> None:
        self._n = 0

    def __call__(self, when: str = _NOW) -> dict[str, str]:
        self._n += 1
        return {
            "event_id": f"c-{self._n}",
            "occurred_at": when,
            "recorded_at": when,
            "correlation_id": "constitution-1",
        }


def _appendix() -> dict[str, object]:
    return json.loads((_ROOT / "example" / "appendix-a.json").read_text(encoding="utf-8"))


def _sealed(document: dict[str, object], private: bytes) -> dict[str, object]:
    return seal(
        document,
        private_key=private,
        key_id="owner-key-1",
        effective_at=_EFFECTIVE,
        expires_at=_EXPIRES,
    )


def _edit(document: dict[str, object], version: int, path: str, value: object) -> dict[str, object]:
    edited = copy.deepcopy(document)
    edited["meta"]["version"] = version
    section, key = path.split(".", 1)
    edited[section][key] = value
    return edited


class ConstitutionTests(unittest.TestCase):
    def test_staging_example_verifies_and_blocks_live(self) -> None:
        pin = json.loads((_ROOT / "config" / "staging.json").read_text(encoding="utf-8"))
        envelope = json.loads((_ROOT / "example" / "staging.signed.json").read_text(encoding="utf-8"))
        public = bytes.fromhex(pin["public_key_hex"])
        version = trade_gate(envelope, public, pin["key_id"], _NOW)
        self.assertEqual(version, 1)
        blockers = live_blockers(envelope["document"])
        self.assertIn("time_lock_placeholder", blockers)
        self.assertIn("broker_balance_cap_unset", blockers)
        self.assertNotIn("private", json.dumps(pin))

    def test_bad_signature_expired_and_unsigned_are_refused(self) -> None:
        private, public = generate_keypair()
        envelope = _sealed(_appendix(), private)
        broken = dict(envelope)
        broken["signature"] = ("0" if envelope["signature"][0] != "0" else "1") + envelope["signature"][1:]
        with self.assertRaises(ConstitutionError) as caught:
            trade_gate(broken, public, "owner-key-1", _NOW)
        self.assertEqual(caught.exception.code, "signature")
        expired = seal(
            _appendix(),
            private_key=private,
            key_id="owner-key-1",
            effective_at="2026-01-01T00:00:00Z",
            expires_at="2026-02-01T00:00:00Z",
        )
        with self.assertRaises(ConstitutionError) as caught:
            trade_gate(expired, public, "owner-key-1", _NOW)
        self.assertEqual(caught.exception.code, "expired")
        unsigned = dict(envelope)
        unsigned["signature"] = ""
        with self.assertRaises(ConstitutionError) as caught:
            trade_gate(unsigned, public, "owner-key-1", _NOW)
        self.assertEqual(caught.exception.code, "unsigned")
        with self.assertRaises(ConstitutionError) as caught:
            trade_gate(envelope, public, "owner-key-1", _NOW, expected_version=9)
        self.assertEqual(caught.exception.code, "version")

    def test_only_one_version_is_active_and_pending_stays_visible(self) -> None:
        private, public = generate_keypair()
        ids = _Ids()
        log = _log()
        first = _sealed(_appendix(), private)
        state = submit_activate(
            log, blank("A"), first, public_key=public, key_id="owner-key-1", now=_NOW, **ids()
        )
        self.assertEqual(view(state)["active_version"], 1)
        self.assertFalse(view(state)["live_permitted"])
        edited = _edit(_appendix(), 2, "risk.max_risk_per_trade_pct", "0.25")
        proposed = _sealed(edited, private)
        state = submit_propose(
            log,
            state,
            proposed,
            public_key=public,
            key_id="owner-key-1",
            now=_NOW,
            reason="lower the per-trade cap",
            **ids(),
        )
        pending = view(state)["pending"]
        self.assertEqual(view(state)["active_version"], 1)
        self.assertEqual(len(pending), 1)
        self.assertTrue(pending[0]["visible"])
        self.assertEqual(pending[0]["lock_state"], "awaiting_owner_hours")
        self.assertEqual(pending[0]["reason"], "lower the per-trade cap")
        self.assertIn("risk.max_risk_per_trade_pct", pending[0]["paths"])
        with self.assertRaises(ConstitutionError) as caught:
            submit_activate(
                log,
                state,
                proposed,
                public_key=public,
                key_id="owner-key-1",
                now="2027-01-01T00:00:00Z",
                **ids("2027-01-01T00:00:00Z"),
            )
        self.assertEqual(caught.exception.code, "time_lock_unset")
        self.assertEqual(replay(log, "A", public_key=public, key_id="owner-key-1").active_json is None, False)
        self.assertEqual(view(replay(log, "A", public_key=public, key_id="owner-key-1"))["active_version"], 1)

    def test_time_lock_uses_the_configured_hours(self) -> None:
        private, public = generate_keypair()
        ids = _Ids()
        log = _log()
        state = submit_activate(
            log,
            blank("A"),
            _sealed(_appendix(), private),
            public_key=public,
            key_id="owner-key-1",
            now=_NOW,
            **ids(),
        )
        hours = copy.deepcopy(_appendix())
        hours["meta"]["version"] = 2
        hours["meta"]["tighten_lock_hours"] = 1
        hours["meta"]["loosen_lock_hours"] = 24
        hours_env = _sealed(hours, private)
        state = submit_propose(
            log,
            state,
            hours_env,
            public_key=public,
            key_id="owner-key-1",
            now=_NOW,
            reason="set the lock hours",
            **ids(),
        )
        state = submit_activate(
            log, state, hours_env, public_key=public, key_id="owner-key-1", now=_NOW, **ids()
        )
        self.assertEqual(view(state)["active_version"], 2)
        self.assertNotIn("time_lock_placeholder", view(state)["live_blockers"])
        self.assertFalse(view(state)["live_permitted"])
        tighter = _edit(hours, 3, "risk.max_risk_per_trade_pct", "0.25")
        tight_env = _sealed(tighter, private)
        proposed_at = "2026-10-22T02:00:00Z"
        state = submit_propose(
            log,
            state,
            tight_env,
            public_key=public,
            key_id="owner-key-1",
            now=proposed_at,
            reason="tighten the per-trade cap",
            **ids(proposed_at),
        )
        with self.assertRaises(ConstitutionError) as caught:
            submit_activate(
                log,
                state,
                tight_env,
                public_key=public,
                key_id="owner-key-1",
                now="2026-10-22T02:30:00Z",
                **ids("2026-10-22T02:30:00Z"),
            )
        self.assertEqual(caught.exception.code, "time_lock")
        state = submit_activate(
            log,
            state,
            tight_env,
            public_key=public,
            key_id="owner-key-1",
            now="2026-10-22T03:00:00Z",
            **ids("2026-10-22T03:00:00Z"),
        )
        self.assertEqual(view(state)["active_version"], 3)
        self.assertEqual(view(state)["predecessor_version"], 2)
        looser = _edit(tighter, 4, "risk.max_risk_per_trade_pct", "0.4")
        loose_env = _sealed(looser, private)
        loose_at = "2026-10-22T04:00:00Z"
        state = submit_propose(
            log,
            state,
            loose_env,
            public_key=public,
            key_id="owner-key-1",
            now=loose_at,
            reason="restore part of the per-trade cap",
            **ids(loose_at),
        )
        with self.assertRaises(ConstitutionError):
            submit_activate(
                log,
                state,
                loose_env,
                public_key=public,
                key_id="owner-key-1",
                now="2026-10-23T03:00:00Z",
                **ids("2026-10-23T03:00:00Z"),
            )
        state = submit_activate(
            log,
            state,
            loose_env,
            public_key=public,
            key_id="owner-key-1",
            now="2026-10-23T04:00:00Z",
            **ids("2026-10-23T04:00:00Z"),
        )
        self.assertEqual(view(state)["active_version"], 4)
        self.assertEqual(len(view(state)["pending"]), 0)

    def test_unordered_lock_hours_are_rejected(self) -> None:
        private, public = generate_keypair()
        log = _log()
        ids = _Ids()
        state = submit_activate(
            log,
            blank("A"),
            _sealed(_appendix(), private),
            public_key=public,
            key_id="owner-key-1",
            now=_NOW,
            **ids(),
        )
        hours = copy.deepcopy(_appendix())
        hours["meta"]["version"] = 2
        hours["meta"]["tighten_lock_hours"] = 24
        hours["meta"]["loosen_lock_hours"] = 24
        with self.assertRaises(ConstitutionError) as caught:
            submit_propose(
                log,
                state,
                _sealed(hours, private),
                public_key=public,
                key_id="owner-key-1",
                now=_NOW,
                reason="set equal lock hours",
                **ids(),
            )
        self.assertEqual(caught.exception.code, "time_lock")

    def test_emergency_tighten_activates_and_loosen_does_not(self) -> None:
        private, public = generate_keypair()
        ids = _Ids()
        log = _log()
        state = submit_activate(
            log,
            blank("A"),
            _sealed(_appendix(), private),
            public_key=public,
            key_id="owner-key-1",
            now=_NOW,
            **ids(),
        )
        tighter = _sealed(_edit(_appendix(), 2, "risk.max_daily_loss_pct", "1"), private)
        state = submit_emergency(
            log,
            state,
            tighter,
            public_key=public,
            key_id="owner-key-1",
            now=_NOW,
            pre_mortem="daily loss cap cut after the halt",
            **ids(),
        )
        self.assertEqual(view(state)["active_version"], 2)
        self.assertEqual(view(state)["predecessor_version"], 1)
        self.assertEqual(view(state)["last_pre_mortem"], "daily loss cap cut after the halt")
        looser = _sealed(_edit(_appendix(), 3, "risk.max_daily_loss_pct", "3"), private)
        with self.assertRaises(ConstitutionError) as caught:
            submit_emergency(
                log,
                state,
                looser,
                public_key=public,
                key_id="owner-key-1",
                now=_NOW,
                pre_mortem="this would loosen the cap",
                **ids(),
            )
        self.assertEqual(caught.exception.code, "emergency_loosen")
        self.assertEqual(
            view(replay(log, "A", public_key=public, key_id="owner-key-1"))["active_version"],
            2,
        )

    def test_emergency_without_a_pre_mortem_does_not_activate(self) -> None:
        private, public = generate_keypair()
        ids = _Ids()
        log = _log()
        state = submit_activate(
            log,
            blank("A"),
            _sealed(_appendix(), private),
            public_key=public,
            key_id="owner-key-1",
            now=_NOW,
            **ids(),
        )
        tighter = _sealed(_edit(_appendix(), 2, "risk.max_daily_loss_pct", "1"), private)
        with self.assertRaises(ConstitutionError) as caught:
            submit_emergency(
                log,
                state,
                tighter,
                public_key=public,
                key_id="owner-key-1",
                now=_NOW,
                pre_mortem="  ",
                **ids(),
            )
        self.assertEqual(caught.exception.code, "pre_mortem")
        self.assertEqual(view(replay(log, "A", public_key=public, key_id="owner-key-1"))["active_version"], 1)

    def test_there_is_no_per_trade_approval(self) -> None:
        names = inspect.signature(trade_gate).parameters
        self.assertNotIn("approval", names)
        self.assertNotIn("approved", names)
        self.assertFalse(hasattr(trade_gate, "approve_trade"))

    def test_bootstrap_records_the_single_activation(self) -> None:
        pin = json.loads((_ROOT / "config" / "staging.json").read_text(encoding="utf-8"))
        public = bytes.fromhex(pin["public_key_hex"])
        with TemporaryDirectory() as directory:
            root = Path(directory)
            fact = root / "fact.db"
            projection = root / "constitution.db"
            FactLog(sqlite3.connect(fact), writers=frozenset({"constitution"}))
            os.environ["SATE_GROUP_SCOPE"] = "A"
            os.environ["SATE_FACTLOG_DB"] = str(fact)
            os.environ["SATE_CONSTITUTION_DB"] = str(projection)
            main()
            opened = FactLog(sqlite3.connect(fact), writers=frozenset({"constitution"}))
            self.assertTrue(matches_replay(projection, opened, "A", public, pin["key_id"]))
            stored = json.loads(projection.read_bytes() and sqlite3.connect(projection).execute(
                "SELECT payload_json FROM projection"
            ).fetchone()[0])
            self.assertEqual(stored["active_version"], 1)
            self.assertFalse(stored["live_permitted"])


if __name__ == "__main__":
    unittest.main()
