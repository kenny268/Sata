"""Advisory-only cognitive plane (**A-COG-01–04** shadow)."""

from sate_cognitive.gate import trading_advisory_multiplier
from sate_cognitive.ingest import IngestResult, ingest_signal

__all__ = ["IngestResult", "ingest_signal", "trading_advisory_multiplier"]
