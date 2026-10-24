"""TG-T-03–05 confirm and K3 double confirm."""

from __future__ import annotations

import unittest

from sate_notifier.confirm import ConfirmError, sign_confirm, verify_confirm
from sate_notifier.flows import accept_confirm, begin_destructive, select_scope
from sate_notifier.state_machine import SessionState


class ConfirmFlowTests(unittest.TestCase):
    def test_expired_confirm_is_rejected(self) -> None:
        token = sign_confirm(action="halt", scope="A", ttl_sec=1, secret=b"secret", now=100)
        with self.assertRaises(ConfirmError):
            verify_confirm(token, secret=b"secret", now=200)

    def test_k3_requires_two_confirms(self) -> None:
        session = SessionState()
        begin_destructive(session, "kill")
        first = select_scope(session, "Group A")
        self.assertIn("confirm_label", first)
        second = accept_confirm(session, str(first["token"]))
        self.assertEqual(second["status"], "await_second_confirm")
        executed = accept_confirm(session, str(second["token"]))
        self.assertEqual(executed["status"], "executed")
        self.assertEqual(executed["result"]["kill_level"], "K3")

    def test_confirm_label_contains_scope(self) -> None:
        session = SessionState()
        begin_destructive(session, "halt")
        picked = select_scope(session, "Group A")
        self.assertIn("A", str(picked["confirm_label"]))


if __name__ == "__main__":
    unittest.main()
