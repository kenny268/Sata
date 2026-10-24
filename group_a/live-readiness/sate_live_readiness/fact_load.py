"""Load LIVE readiness attestations from the fact log."""

from __future__ import annotations

import os
from dataclasses import dataclass

from sate_factlog.errors import Unauthorized
from sate_factlog.log import FactLog

READER_ID = "live-readiness-a"


@dataclass(frozen=True)
class LoadedLiveReadinessState:
    rcb_at_or_above_floor: bool = False
    constitution: dict[str, object] | None = None
    design_review_complete: bool = False
    inv_suite_green: bool = False
    matrix_green: bool = False
    sim_adequacy_attested: bool = False
    written_broker_verification: bool = False
    cg_live_confirmed: bool = False
    rpo_rto_resolved: bool = False

    def any_present(self) -> bool:
        return any(
            (
                self.rcb_at_or_above_floor,
                self.constitution is not None,
                self.design_review_complete,
                self.inv_suite_green,
                self.matrix_green,
                self.sim_adequacy_attested,
                self.written_broker_verification,
                self.cg_live_confirmed,
                self.rpo_rto_resolved,
            )
        )


def load_live_readiness_state(
    log: FactLog,
    *,
    as_of: str,
    reader_id: str | None = None,
) -> LoadedLiveReadinessState:
    rows = _replay(log, as_of=as_of, reader_id=reader_id)
    rcb = False
    constitution: dict[str, object] | None = None
    design = False
    inv = False
    matrix = False
    sim = False
    written = False
    cg = False
    rpo = False
    for row in rows:
        kind = row.payload.get("kind")
        if kind == "live_rcb_floor_attestation" and row.payload.get("at_or_above_floor"):
            rcb = True
        elif kind == "live_constitution_snapshot":
            constitution = {
                "meta": dict(row.payload.get("meta", {})),  # type: ignore[arg-type]
                "risk": dict(row.payload.get("risk", {})),  # type: ignore[arg-type]
                "mode": dict(row.payload.get("mode", {"state": "SIM"})),  # type: ignore[arg-type]
            }
        elif kind == "live_design_review_gate" and row.payload.get("complete"):
            design = True
        elif kind == "live_inv_suite_attestation" and row.payload.get("green"):
            inv = True
        elif kind == "live_verification_matrix_attestation" and row.payload.get("green"):
            matrix = True
        elif kind == "live_sim_adequacy_attestation" and row.payload.get("gate_met"):
            sim = True
        elif kind == "live_written_broker_verification" and row.payload.get("on_file"):
            written = True
        elif kind == "live_cg_live_confirmation" and row.payload.get("initial_advisory_zero"):
            cg = True
        elif kind == "live_rpo_rto_attestation" and row.payload.get("owner_set"):
            rpo = True
    return LoadedLiveReadinessState(
        rcb_at_or_above_floor=rcb,
        constitution=constitution,
        design_review_complete=design,
        inv_suite_green=inv,
        matrix_green=matrix,
        sim_adequacy_attested=sim,
        written_broker_verification=written,
        cg_live_confirmed=cg,
        rpo_rto_resolved=rpo,
    )


def _replay(log: FactLog, *, as_of: str, reader_id: str | None) -> list:
    preferred = reader_id or os.environ.get("SATE_LIVE_READINESS_READER", READER_ID)
    candidates: list[str] = []
    for item in (preferred, READER_ID, "control-api", "compliance-a"):
        if item not in candidates:
            candidates.append(item)
    last: Exception | None = None
    for candidate in candidates:
        try:
            return log.replay_through(group_scope="A", as_of=as_of, reader_id=candidate)
        except Unauthorized as exc:
            last = exc
    if last is not None:
        raise last
    return []
