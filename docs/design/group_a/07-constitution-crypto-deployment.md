# Constitution, change control, and kernel deployment

**Source:** Group A §8; Appendix A; **A-CON-***; **A-P0-07**, **A-P0-19**.

---

## 1. Constitution as signed configuration (§8.1)

Versioned signed object loaded by KERNEL-A. **Configuration authority**, not a substitute for code-level safety.

| Field class | Contents |
|-------------|----------|
| Identity | `constitution_id`, version, group A, `effective_at` |
| Universe | Instruments per state/rung |
| Risk | Per-trade caps, notional, leverage, margin, concentration |
| Capital | RCB policy refs, cash floor, ratification refs |
| Execution | Slippage budgets, order types, protective-stop policy |
| Modes | SIM/LIVE permissions, ramp, transitions |
| Treasury | Cost allocation, obligations, broker assignment, reserves |
| Operations | Check-in, dead-man, away-mode max |
| Safety | Halt thresholds, kill scopes, escalation |
| Security | Allowed key IDs, artifact constraints, trust anchors |
| Audit | Change reason, owner action ref, predecessor version |

Example structure: [15-persistent-schemas-constitution.md](./15-persistent-schemas-constitution.md) (Appendix A).

---

## 2. Change lifecycle (§8.2)

```
proposal → validation → authorization → time-lock → effective-time check
  → signed artifact → kernel verification → activation → fact-log record
```

**Emergency tightening only:**

```
signed emergency command → validate tighten-only → activate → audit + pre-mortem
```

**Emergency loosening prohibited.**

| ID | Rule |
|----|------|
| **A-CON-01** | Kernel verifies signature, version, key ID, effective time; refuse unsigned/invalid/expired |
| **A-CON-02** | Time-lock before effect; tighten lock shorter than loosen (**A-DEC-04** durations) |
| **A-CON-03** | Pending changes visible; lock state + timestamps logged |
| **A-CON-04** | No per-trade approval workflow |

Web: Constitution page read-only + pending changes + countdown (§13.3).

---

## 3. Kernel build and deployment pipeline (§8.3)

| Stage | Implementation | Evidence |
|-------|----------------|----------|
| Proposal | Change ID, revision, reason, safety domains | Change record |
| Time-lock | Policy applied | Lock state |
| Reproducible build | Pinned deps, deterministic env | Build manifest hash |
| Signed artifact | Build identity signs artifact | Signature |
| Deployment authorization | Owner-authorised install | Auth event |
| Frozen red-team regression | Required suite on exact artifact; fail closed if missing | Suite version + results |
| Deployment | Verify artifact + Constitution before activation | Deployment record |

### 3.1 Cryptographic authority scopes

| Authority | Scope | Cannot |
|-----------|-------|--------|
| Build identity | Sign build + artifact identity | Authorise deploy or Constitution |
| Deployment authorization | Install verified artifact | Imply second human operator |
| Constitution authorization | Sign Constitution | Sign kernel artifact |
| Emergency tightening | Risk-reducing emergency config | Loosen risk |

One human operator; distinct keys separate **technical scopes** only.

**R-85:** Pinned verify key at install; rotation procedure; suspected compromise → **K3** + re-provision.

---

## 4. Constitution ↔ kernel coupling

- Kernel loads active Constitution at startup and checks version on each verdict metadata.
- Constitution change does not bypass kernel code checks (dual layer).
- Promotion gates (§15.8) **never** loosen kernel limits via model promotion.

---

## 5. Placeholder fields tied to decisions

| Field (Appendix A) | Decision |
|--------------------|----------|
| `tighten_lock_hours`, `loosen_lock_hours` | A-DEC-04 |
| `LIVE-L2` universe | A-DEC-02 |
| `max_risk_per_trade_pct` | A-DEC-01 |
| `cost_allocation` | A-DEC-05 |
| `broker_balance_cap = 0` | Owner-defined; 0 blocks LIVE |
