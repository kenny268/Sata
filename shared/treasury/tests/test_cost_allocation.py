import sqlite3
import unittest
from decimal import Decimal

from sate_factlog.log import FactLog
from sate_treasury.cost_allocation import pro_rata_rcb_shares, shared_cost_payload
from sate_treasury.ledger import blank
from sate_treasury.sourced import submit_shared_cost


class _Ids:
    def __init__(self) -> None:
        self._n = 0

    def __call__(self) -> dict[str, str]:
        self._n += 1
        return {
            "event_id": f"alloc-{self._n}",
            "occurred_at": "2026-10-23T00:00:00Z",
            "recorded_at": "2026-10-23T00:00:01Z",
            "correlation_id": "cost-alloc",
        }


class CostAllocationTests(unittest.TestCase):
    def test_pro_rata_rcb_shares(self) -> None:
        shares = pro_rata_rcb_shares(amount="100.00", rcb_a="300", rcb_b="200")
        self.assertEqual(shares["A"], "60.00")
        self.assertEqual(shares["B"], "40.00")

    def test_shared_cost_event(self) -> None:
        log = FactLog(sqlite3.connect(":memory:"), writers=frozenset({"treasury"}))
        payload = shared_cost_payload(
            cost_id="infra-1",
            amount="100.00",
            currency="USD",
            vendor="hosting",
            evidence="invoice-1",
            path="owner_paid",
            rcb_a="500",
            rcb_b="500",
        )
        state = submit_shared_cost(log, blank(), payload, **_Ids()())
        self.assertEqual(len(state.allocations), 1)
        self.assertEqual(Decimal(state.allocations[0].share_a), Decimal("50"))
        self.assertEqual(Decimal(state.allocations[0].share_b), Decimal("50"))


if __name__ == "__main__":
    unittest.main()
