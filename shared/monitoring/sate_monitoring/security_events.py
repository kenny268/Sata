"""Control-api and security boundary events → alerts (**§14.1**)."""

from __future__ import annotations

from dataclasses import dataclass, field

from sate_monitoring.alerts import CriticalAlert
from sate_monitoring.on_call import OnCallRouter


@dataclass
class SecurityEventRecorder:
    on_call: OnCallRouter = field(default_factory=OnCallRouter)

    def permission_denied(self, detail: str) -> None:
        self.on_call.dispatch(
            CriticalAlert(
                group_scope="A",
                code="control_auth_failure",
                message=detail,
                severity="HIGH",
            )
        )

    def rate_limited(self, client: str) -> None:
        self.on_call.dispatch(
            CriticalAlert(
                group_scope="A",
                code="control_rate_limited",
                message=f"client={client}",
                severity="NOTICE",
            )
        )

    def scope_violation(self, detail: str) -> None:
        self.on_call.dispatch(
            CriticalAlert(
                group_scope="A",
                code="scope_violation",
                message=detail,
                severity="HIGH",
            )
        )
