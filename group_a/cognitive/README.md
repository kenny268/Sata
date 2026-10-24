# Group A cognitive plane (Phase 21)

Signed **AdvisorySignal** ingestion only — no broker, kernel, or order imports (**SEC**).

| ID | Behavior |
|----|----------|
| **A-COG-01** | Invalid/malformed/expired/unsigned → zero trading view |
| **A-COG-02** | Calibration table caps `c` at `C_MAX_START` (0.3) for shadow |
| **A-COG-03** | Evidence refs scanned for injection patterns → abstain |
| **A-COG-04** | Weekly SIM shadow report (`weekly_runner`); **CG-LIVE** numeric threshold **not** defined |

**Trading gate:** `trading_advisory_multiplier()` is **0** for all account modes until a future **CG-LIVE** gate. Strategy uses `cognitive_wire.advisory_view_for_blend()` so Kalman-only paths continue (**TS-02**).

Schema: `shared/schemas/advisory-signal.schema.json`.

SIM: `sim_cognitive` + `sim_loop` record shadow ingests; `demo_marathon` writes state (`SATE_SHADOW_STATE_FILE`) and fact-log `advisory_signal` events. Weekly export: `weekly_runner` reads state when present.

Compose: `cognitive`, `cognitive-shadow-weekly`.

Still later phases: **CG-LIVE** threshold, live multiplier, full §11.3 validator matrix, Telegram templates, prompt retention, production signer transport.
