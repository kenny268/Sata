"""Fact log chain integrity → CRITICAL (**A-P0-17**)."""

from __future__ import annotations

from sate_factlog.log import FactLog

from sate_monitoring.alerts import AlertRouter, CriticalAlert


def check_chain(log: FactLog, *, reader_id: str, router: AlertRouter) -> int | None:
    broken = log.verify(reader_id=reader_id)
    if broken is not None:
        router.route(
            CriticalAlert(
                group_scope="A",
                code="factlog_chain_broken",
                message=f"fact log integrity failure at seq {broken}",
            )
        )
    return broken
