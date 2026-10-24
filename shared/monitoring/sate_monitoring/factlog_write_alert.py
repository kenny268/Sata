"""Fact log write failures → alerts (**§14.1**, no silent recovery)."""

from __future__ import annotations

from sate_factlog.errors import FactLogWriteError

from sate_monitoring.alerts import CriticalAlert
from sate_monitoring.on_call import OnCallRouter


def alert_on_write_failure(exc: FactLogWriteError, *, router: OnCallRouter) -> None:
    severity = "CRITICAL" if exc.policy == "BLOCK" else "HIGH"
    router.dispatch(
        CriticalAlert(
            group_scope="A",
            code="factlog_write_failure",
            message=str(exc),
            severity=severity,
        )
    )
