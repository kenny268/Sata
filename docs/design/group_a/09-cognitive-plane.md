# Cognitive plane interface (Group A)

**Source:** Group A §11; **A-COG-***; scenario TS-02, TS-03; Telegram ABSTAIN/ERROR templates.

---

## 1. Authority boundary

The cognitive plane:

- Publishes **signed advisory signals** only.
- Has **no** order, sizing, credential, Constitution, or kernel authority.
- Failure **cannot create a trade** (**INV-07**).

Group A: tick-level signals, short horizons; **TTL < horizon**; expired = zero view.

---

## 2. AdvisorySignal schema (§11)

```
signal_id, cycle_id, instrument, horizon,
state: ACTIVE | ABSTAIN,
q,                    # signed expected return, capped ± q_max
c,                    # calibrated confidence [0, c_max]
evidence_refs[],
valid_from, valid_until,
model_id, prompt_hash, calibration_version,
abstain_reason?,
signature             # Ed25519, reasoning-graph key
```

**Black–Litterman mapping:**

- `Q = q`
- `Omega = ((1 - c) / c) * P (tau * Sigma) P^T`
- ABSTAIN or expired → no view row (Omega → ∞)

Blending detail: [04-strategy-quant-engine.md](./04-strategy-quant-engine.md) §2.

---

## 3. Validator outcomes (§11)

| Condition | Output |
|-----------|--------|
| Malformed schema | Reject signal; log validator failure |
| Evidence conflict / unresolved skeptic | ABSTAIN |
| Stale evidence / point-in-time violation | ABSTAIN |
| Tool failure / budget exhaustion | ABSTAIN |
| Multi-sample directional disagreement (if enabled) | ABSTAIN |
| Invalid/expired signature | Reject; no downstream view; rising failure rate → WARN |

---

## 4. Requirements

| ID | Rule |
|----|------|
| **A-COG-01** | Advisory view **zero** when no valid unexpired signed signal |
| **A-COG-02** | `c` from calibration table (shadow fit); until samples sufficient, **c_max low (0.3 starting)** |
| **A-COG-03** | Retrieved text = data not instruction; injection/malformed/stale/budget → ABSTAIN or zero |
| **A-COG-04** | Evaluate vs advisory=0 baseline (rank corr, calibration, P&L); **CG-LIVE** gate (**implementation Phases 25–27**) for live advisory — **threshold not defined**; do not invent |

---

## 5. Operational behaviour

| Scenario | Behaviour |
|----------|-----------|
| Plane unavailable (TS-02) | Zero advisory; Kalman path continues |
| Abstention (TS-03) | ABSTAIN reason; digest-only Telegram where applicable |
| Tool failure (Telegram ERROR) | Advisory zeroed; WARN message |
| Infra cap / LLM budget (CT-08) | Advisory view zero |

**A-P1-05:** Champion/challenger machinery evaluates advisory in **shadow**; live advisory contribution gated by owner-approved **A-COG-04** methodology.

---

## 6. Security

- Verify Ed25519 signature on every signal before BL step.
- Prompt hash stored for audit; prompts/responses retained **12 months** (§12.4).
- Prompt injection cannot reach kernel or broker (**SEC** tests §16).
