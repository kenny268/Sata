# Group A LIVE readiness (Phase 25)

| ID | Module |
|----|--------|
| **A-P1-06** | `preflight_engine.assess_live_readiness` — explicit §19 / INV / decision reason codes |
| **A-COG-04** | `cg_live.py` + `shared/ci/cg-live-record.json` (initial LIVE = advisory **0**) |
| **A-DEC-04** | Constitution lock hours via `a_dec_04_reasons` |
| **A-DEC-09** | RPO/RTO via `shared/ci/a-dec-09-rpo-rto.json` + deploy env |
| **§16.1** | `shared/ci/verification-matrix.json` |
| **§17.1** | `design_review.py` — `SATE_DESIGN_REVIEW_COMPLETE` |

`/mode/A/arm` merges **`live_readiness`** assessment with broker gate and AM-02/03 checks. Default path loads §19 attestations from the **fact log** (`live_ops_wire.inputs_for_arm`, writer **`live-readiness-a`**). Use **`seed_staging_live_readiness(log)`** for a full staging bundle (broker + SIM harness + attestations), or **`live_readiness_complete: true`** in tests to bypass log loading.

Attestations: RCB floor, constitution snapshot, design review, INV/matrix, SIM adequacy, written broker verification, CG-LIVE, RPO/RTO — see `persist.py`.

Runner: `python -m sate_live_readiness.phase25_runner` (`SATE_LIVE_READINESS_FACTLOG`, `SATE_PHASE25_REPORT_DIR`).
