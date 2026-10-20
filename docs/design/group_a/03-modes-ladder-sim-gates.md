# Operating modes, ladder, SIM→LIVE, and SIM-adequacy

**Source:** Group A §4; scenarios §15.4 (AM-*), §15.6 (OP-*); **A-MOD-***, **A-SWT-***, **A-LAD-***, **A-SIM-***.

---

## 1. Trading states (§4.1)

| State | Entry | Permitted behaviour | Exit |
|-------|-------|---------------------|------|
| **SIM** | Default / deferred / LIVE not authorised | Generate intents; **no live exposure** | SIM-adequacy + preflight + owner auth |
| **LIVE-L1** | Group A LIVE gate passes | Ramped live; reduced universe; shadow twin; heightened monitoring | L2 graduation, reverse grad, halt |
| **LIVE-L2** | L2 evidence satisfied | L2 Constitution limits | L3, reverse grad, halt |
| **LIVE-L3** | L3 requirements satisfied | Highest rung; all kernel limits | Reverse grad, retirement, halt |
| **MANAGE_ONLY** | Owner absence, mode transition, halt | Manage/reduce; **no new risk-increasing entries** | Re-arm or flatten |
| **HALTED** | L2+, L3, L4, kill | No new risk-increasing; approved recovery/reduce only | Recovery gate + owner auth |

**A-DEC-02:** L2/L3 graduation criteria and universes — **BLOCKED** for implementation beyond placeholders.

---

## 2. Account identification (§4.2)

| ID | Requirement | Implementation note |
|----|-------------|------------------------|
| **A-MOD-01** | Strategy mode-agnostic; kernel resolves SIM/LIVE profile | Same code path SIM and LIVE |
| **A-MOD-02** | Fingerprint (account # + server) at startup, reconnect, intervals; mismatch → **immediate halt**, no orders | HL-C |
| **A-MOD-03** | Every record/metric/notification carries `account_mode`; never sum SIM+LIVE | Reporting layer |
| **A-MOD-04** | Web badge LIVE=red, SIM=blue; Telegram `[A-LIVE]` / `[A-SIM]` | TG-01, A-TG-01 |
| **A-MOD-05** | No live credentials on SIM host path where broker allows | Separate MT5 terminals |

---

## 3. SIM → LIVE (risk-increasing) (§4.3)

| Step | Action | Control |
|------|--------|---------|
| 1 | Owner requests LIVE in web | Passkey (or TOTP) re-auth |
| 2 | Preflight | Automatic pass/fail **reason codes** |
| 3 | Arming | Default **24h** cancellable (web or Telegram cancel) |
| 4 | Confirmation | **OTP via Telegram**, entered **only in web** (TG-16, OI-TG-01) |
| 5 | Safe window | Kernel schedules (flat or market closed) |
| 6 | Ramp | Reduced limits per Constitution (e.g. **0.25×**, **30 days**) |

### 3.1 Preflight checklist (all required)

- SIM-adequacy §4.5 + Group A capital only (not combined).
- Reconciliation clean; slippage within budget; no L2+ in window.
- Kernel red-team suite on deployed build.
- Live profile; fingerprint verified (read-only); trade-only API key where checkable.
- Balance within per-broker cap; treasury cash floor/obligations satisfied.
- No active halt, pending Constitution change, or kill state.
- Broker rules verified for exact account type (§7.4).
- Reference floor satisfied by **RCB**, not raw equity or combined dashboard.
- Ramp initialised (**0.25×** where applicable); 30-day minimum start persisted.

Engine: **A-P1-06** LIVE preflight with explicit reasons.

---

## 4. LIVE → SIM (risk-reducing) (§4.4)

| ID | Rule |
|----|------|
| **A-SWT-01** | Any time from web or Telegram; immediate for new entries; **no effect on B** |
| **A-SWT-02** | LIVE → **MANAGE_ONLY**; exits via stops/rules; optional flatten |
| **A-SWT-03** | Shadow twin: parallel SIM intents while LIVE; record divergence |
| **A-SWT-04** | SIM fills optimistic; good SIM necessary not sufficient; first LIVE ramped |

Telegram: [telegram-interface.md](./telegram-interface.md) §5.3 mode-to-SIM.

---

## 5. Three clocks (§4.5)

| Control | Meaning |
|---------|---------|
| **0.25× ramp** | Stored in Group A state + fact log |
| **30-day minimum ramp** | Persist start timestamp; no early graduation |
| **90-day clean evidence** | Independent of ramp clock |
| **Shadow twin** | Same intents in SIM while LIVE |
| **Reverse graduation** | Group A only; B unaffected |

**A-LAD-04:** No mode switch during ramp quiet period.

---

## 6. Floor protection and reverse graduation (§4.5)

| ID | Rule |
|----|------|
| **A-LAD-01** | Every broker poll: WARN if equity within **10%** above floor; if crosses floor → reject new intents + WARN in verdict |
| **A-LAD-02** | **3 consecutive sessions** below floor → auto return to SIM; LIVE → MANAGE_ONLY |
| **A-LAD-03** | Re-entry: RCB recovery + cool-off; not within **14 days** of breach; full preflight |
| **A-LAD-04** | No mode switch during ramp quiet period |
| **A-LAD-05** | Drawdown beyond ramp threshold → auto SIM (starting proposal **20%** — Constitution field; confirm in A-DEC-02) |
| **A-LAD-06** | All graduations/reverse graduations deterministic, fact-logged, reproducible |

Telegram: RISK WARN / MODE WARN messages — [telegram-interface.md](./telegram-interface.md) §6.4, §6.7.

---

## 7. SIM-adequacy (all required) (§4.5)

| ID | Criterion |
|----|-----------|
| **A-SIM-01** | ≥ **6 months** continuous SIM at reference floor sizing |
| **A-SIM-02** | Clean reconciliation ≥ **95%** of sessions |
| **A-SIM-03** | Net Sharpe ≥ **1.2** after modelled costs |
| **A-SIM-04** | Net monthly return ≥ **6%** over 3 rolling months at last 3 month-ends (actual cost allocation); hurdle under **A-DEC-03** |
| **A-SIM-05** | ≥ **200 trades** OR bootstrap CI on excess return with positive lower bound |
| **A-SIM-06** | No unresolved L2+ in final **60 days** |
| **A-SIM-07** | Frozen strategy version: **no parameter changes** in final **3 months** |
| **A-SIM-08** | Record survives floor-scale sizing (not systematically `untradeable_at_this_capital`) |

Engine: **A-P1-01** — reproducible gate report from stored evidence.

---

## 8. Minimum lot vs ramp (§4.5) — **A-DEC-01**

Illustrative EUR/USD 0.01 lot ≈ **$0.10/pip** (verify with broker).

| Stop | Cap | Ramp | Effective cap | Risk 0.01 lot | Capital needed |
|------|-----|------|---------------|---------------|----------------|
| 20 pips | 0.5% | none | 0.5% | $2.00 | $400 |
| 20 pips | 0.5% | 0.25× | 0.125% | $2.00 | **$1,600** |
| 20 pips | 1.0% | none | 1.0% | $2.00 | $200 |
| 10 pips | 0.5% | 0.25× | 0.125% | $1.00 | $800 |

At **0.5%** cap, 20-pip stop, **$500** supports one min lot **only without ramp scaling**. With **0.25×** ramp, required capital exceeds $500 → **A-DEC-01** before LIVE gate.

---

## 9. Owner check-in (§9.4) while LIVE

| Days without check-in | State | Behaviour |
|----------------------|-------|-----------|
| 7 | Reminder | Telegram + email daily; no trading change |
| 10 | MANAGE_ONLY | Stops/exits only |
| 14 | Flatten | All LIVE positions closed; terminal stop; web re-arm |

**A-CHK-01–05:** Timer in **kernel**; `/alive` = presence not privilege; away mode via web passkey.

SIM during lapse: **continues** (OP-05) for uninterrupted SIM record.

---

## 10. Mode scenario index (§15.4)

| ID | Summary |
|----|---------|
| AM-01 | SIM→LIVE full flow |
| AM-02 | Cancel arming |
| AM-03 | Preflight fail → reason codes |
| AM-04 | LIVE→SIM → MANAGE_ONLY |
| AM-05 | LIVE→SIM + flatten |
| AM-06 | B mode change → no A effect |
| AM-07 | Wrong account → HL-C |
| AM-A1 | L1→L2 graduation (A-DEC-02) |
| AM-A2 | Mode switch during ramp → refused |
| AM-A3–A7 | Floor warnings, reverse graduation, ramp drawdown |

Full tables: [13-scenarios-runbooks.md](./13-scenarios-runbooks.md).
