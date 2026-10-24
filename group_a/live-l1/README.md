# Group A LIVE-L1 (Phase 26)

| ID | Module |
|----|--------|
| **AM-01** | `arming_delay` — 24h wait (`SATE_ARMING_DELAY_HOURS`, `0` in staging tests) |
| **OI-TG-01** | `telegram_otp.deliver_arm_otp` — OTP logged; entry **web-only** on confirm |
| **A-LAD-04–06** | `ramp` — **0.25×** start, 30-day minimum, quiet period |
| **A-SWT-03** | `shadow_twin` — parallel SIM session while LIVE-L1 |
| **C.4** | `c4_runbook` + `transition.activate_live_l1` |

Flow: preflight arm → Telegram OTP event → delay → **`POST /mode/A/confirm`** (passkey + OTP) → safe window + ramp + shadow twin → `run_first_live_session` with mandatory post-session recon.

Staging confirm: `live_l1_staging: true` or `arming_delay_elapsed: true`. Runner: `python -m sate_live_l1.phase26_runner`.

Operator: `first_production_session_on_broker` in `phase-26-tracker.json` when real Exness LIVE session completes.
