"""control-api integration for reduce-only commands (**TG-PO-09**).

Without a bound control plane the command is validated and not issued.
"""

from __future__ import annotations

from collections.abc import Callable

from sate_control.kill import validate_kill

Dispatch = Callable[[dict[str, object]], dict[str, object]]

_KILL_ACTION = {"K1": "halt", "K2": "flatten", "K3": "kill"}


def submit_kill(
    *,
    scope: str,
    kill_level: str,
    dispatch: Dispatch | None = None,
) -> dict[str, object]:
    payload = validate_kill(scope=scope, kill_level=kill_level, channel="telegram")
    body = {
        "action": _KILL_ACTION[kill_level],
        "scope": scope,
        "channel": "telegram",
        "kill_level": kill_level,
    }
    return _issue(payload, body, dispatch)


def submit_mode_sim(
    *,
    scope: str,
    flatten: bool = False,
    dispatch: Dispatch | None = None,
    action: str = "mode_sim",
) -> dict[str, object]:
    if scope != "A":
        raise ValueError("mode sim via telegram is Group A scoped")
    if action not in {"mode_sim", "cancel_arm"}:
        raise ValueError("telegram mode action is not reduce-only")
    payload: dict[str, object] = {"scope": scope, "mode": "SIM", "channel": "telegram"}
    body: dict[str, object] = {"action": action, "scope": scope, "channel": "telegram"}
    if flatten:
        body["action"] = "mode_sim_flatten"
        payload["flatten"] = "K2"
    return _issue(payload, body, dispatch)


def _issue(
    payload: dict[str, object],
    body: dict[str, object],
    dispatch: Dispatch | None,
) -> dict[str, object]:
    if dispatch is None:
        return {**payload, "issued": "false"}
    control = dispatch(body)
    return {**payload, "issued": "true", "control": control}
