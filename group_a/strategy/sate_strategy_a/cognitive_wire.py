"""Strategy boundary for cognitive plane (**INV-07**)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sate_cognitive.ingest import IngestResult


def advisory_view_for_blend(result: IngestResult | None) -> float | None:
    if result is None or not result.ok:
        return None
    return result.trading_view
