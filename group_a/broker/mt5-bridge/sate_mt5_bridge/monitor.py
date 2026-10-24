"""Export bridge state for Group A monitoring."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sate_mt5_bridge.bridge import Bridge


def observation_from_bridge(bridge: Bridge, *, poll_failures: int = 0) -> dict[str, object]:
    latency_ms = max(0, bridge.latency_us // 1000)
    return {
        "group_scope": "A",
        "adapter_state": bridge.state,
        "poll_failures": poll_failures,
        "latency_ms": latency_ms,
    }
