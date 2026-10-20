# Verification, invariants, risks, LIVE gates, and implementation backlog

**Source:** Group A §16–19, §18, §17; Telegram §14–16 (TG-T, DoD).

---

## 1. Test hierarchy (§16.1)

| Class | Group A scope | Pass condition |
|-------|---------------|--------------|
| **UT** | Deterministic calcs, schemas, state transitions, auth rules, costs | No untested safety-critical branch |
| **IT** | Component contracts, event flows | Expected events/transitions |
| **BAT** | Adapter auth, fingerprint, orders, fills, positions, balances, outages, rate limits | No contract ambiguity |
| **REC** | Mismatch, duplicate, stale, broker truth | Discrepancy detected; no unsafe duplicate |
| **STM** | SIM/LIVE/rung, halt, kill, treasury states | Invalid transitions rejected |
| **INV** | Isolation, no bypass, no equity→withdrawable, halt invariant | Never violated |
| **SEC** | Auth, key scope, replay, injection, secrets, artifacts | Unauthorised blocked |
| **RT** | Bypass, wrong account, stale state, oversized order, clock skew, duplicate | Blocked + logged |
| **FI** | Network loss, kill process, broker timeout, stale data, DB failure | Fail closed; recover via recon |
| **DR** | Backup restore, host rebuild, fact-log integrity | Full recovery verified |
| **DEP** | Reproducible build, signature, rollback, artifact identity | Only authorised verified artifact runs |
| **TRE** | Invoice, FX, reserves, reimbursement, missed deadline | No false withdrawal complete |
| **HALT** | A/B/ALL scope, partial ack, unreachable kernel, recovery | HALT_CONFIRMED_ALL invariant |
| **ISO** | Cross-group injection | No authority leakage |
| **PERF** | Kernel latency, ingestion, recon windows | Within targets or blocker filed |
| **MOD** | Champion/challenger, ablation, probation rollback | Gate enforced |
| **OPS** | Owner absence, incidents, runbooks, monthly restore, kill drills | Operator executes runbook |
| **TG** | TG-T-01–15 | All pass ([telegram-interface.md](./telegram-interface.md)) |

---

## 2. Group A-specific tests (§16.2)

| Test | Method | Pass |
|------|--------|------|
| Minimum-lot sizing | Floor capital ± ramp | Untradeable rejected; never round up |
| Reverse graduation drill | Drive equity below floor in SIM | WARN +10%; SIM after 3 sessions; B unchanged; no re-entry 14d |
| Ramp clock | Graduate before 30d or before 90 clean | Refused |
| Ramp quiet period | Mode switch during ramp | Refused |
| Shadow twin divergence | SIM beside LIVE + injected slippage | Divergence recorded |
| MT5 bridge disconnect | Kill mid-order | No duplicate; recon before resume |
| Wrong terminal | Demo login while LIVE armed | Fingerprint halt |
| Swap and blackout | Entries in window | Rejected |
| Cross-group invariants | Combined capital/RCB injection | Rejected; A unaffected by B |

---

## 3. Required invariants (§16.3)

| ID | Invariant |
|----|-----------|
| INV-01 | No broker order without valid kernel verdict |
| INV-02 | A risk services never consume B capital/RCB (and reverse) |
| INV-03 | Combined dashboard values cannot reach sizing/eligibility |
| INV-04 | Equity never treated as withdrawable cash |
| INV-05 | Reimbursement incomplete until broker movement reconciled |
| INV-06 | Kernel unreachable ≠ HALT_CONFIRMED_ALL |
| INV-07 | Cognitive failure cannot create trade |
| INV-08 | Unknown broker rules cannot silently enable LIVE capability |
| INV-09 | RCB increase cannot bypass cool-off + ratification |
| INV-10 | A state transition cannot mutate B state |
| INV-11 | Safety-critical transitions produce auditable fact |

Automated **INV** + **ISO** suites in CI for every release (§17.1 item 2).

---

## 4. Risk register (Group A cited IDs, §17)

| ID | Risk | Sev | Primary controls |
|----|------|-----|------------------|
| R-01 | No demonstrated positive expectancy | S1 | SIM-adequacy §4.5; A-PERF-02 |
| R-02 | Order without kernel approval | S1 | A-KRN-01; RT |
| R-03 | Exness counterparty | S1 | broker_balance_cap; §15.7 |
| R-04 | Undetectable failure | S1 | §9 halts/kill |
| R-05 | Owner changes rules under stress | S1 | time-lock; RCB |
| R-07 | Over-bet from estimated edge | S1 | §5.3 sizing |
| R-08 | Unrealistic strategies (e.g. retail arb) | S2 | §5.5 research gates |
| R-12 | Fact log drift; duplicate retries | S1 | §6.5–6.6 |
| R-13 | Incomplete cost model | S2 | §10.2 |
| R-17 | Wrong account/terminal | S1 | §4.2 fingerprint |
| R-18 | Hijacked TG/web | S1 | §9.2, §13.4 asymmetry |
| R-19 | Unprotected offline positions | S1 | broker stops |
| R-21 | Calendar/rollover/gaps | S2 | §6.4 checks |
| R-23 | SIM mistaken for live capital | S1 | mode tagging |
| R-24 | Overfitting via return gate | S1 | frozen strategy; sizing bounds |
| R-25 | Min lot at small capital | S2 | A-DEC-01 |
| R-34 | $500 floor as target | S1 | SIM gate; RCB cool-off |
| R-35 | Narrow L1 universe | S2 | Constitution |
| R-36 | Below floor after LIVE | S1 | A-LAD-* |
| R-37 | Single gate insufficient | S2 | A-SIM-08 |
| R-41 | Pooled capital | S1 | §1.3 |
| R-42 | Cross-group rescue | S1 | no transfer API |
| R-47 | Ambiguous shared-cost allocation | S2 | A-DEC-05 |
| R-50 | BL degeneracy one instrument | S2 | §5.2 |
| R-52 | Kalman tuning overfit | S2 | challenger gate |
| R-58 | Poll misses fast drawdown | S2 | fill-driven updates |
| R-60 | Latency target unvalidated | S2 | shadow measurement |
| R-64 | Floor oscillation | S2 | 3-session + 14d block |
| R-65 | Kill one system not other | S2 | explicit scope |
| R-66 | Trusted contact misuse | S2 | runbook |
| R-67 | Long away hides failure | S2 | auth; max under review |
| R-78 | Windows attack surface | S2 | minimal software; firewall |
| R-79 | Clock skew | S2 | NTP; broker time |
| R-85 | Pinned key compromise | S1 | rotation; K3 |
| R-86 | Tax/reporting cross-border | S2 | A-DEC-10; A-FEE-05 |

---

## 5. Design review at every gate (§17.1)

1. Pre-mortem: assume 30% loss in 90d — three causes + controls.
2. Red-team kernel/interfaces (§16) each release.
3. Ablation: drop component if results don’t worsen without it.
4. Cost audit from real fills + invoices.
5. Complexity budget: trigger + failure mode + auto response per new component.
6. Assumption register (Appendix D) — stale blocks gate.
7. Two-system consistency — no capital fungibility assumption.
8. State audit — mode matches RCB + universe.

---

## 6. Implementation backlog (§18)

See [implementation-phases.md](./implementation-phases.md) for phase mapping. Summary:

| Priority | IDs | Notes |
|----------|-----|-------|
| P0 | A-P0-01 – A-P0-20 | Required before LIVE |
| BLOCKED | A-P0-21 | A-DEC-01 |
| P1 | A-P1-01 – A-P1-07 | L2/L3 in A-P1-02 blocked on A-DEC-02 |
| P2 | A-P2-01 | Research modules gated |

**P0 build sequence (§18.1):** traceability → account registry → fact log → capital/treasury → RCB/Constitution → crypto/deploy pipeline → kernel+MT5 → OMS/recon → halt/kill → web/TG → monitoring/backup → broker verification → resolve blockers → P0 tests + drills.

Telegram: **TG-PO-01–15** ([telegram-interface.md](./telegram-interface.md)).

---

## 7. Definition of Done (§19)

| Area | Complete when |
|------|---------------|
| Architecture | Authority boundaries; A/B independence in contracts/APIs/kernel |
| Code | P0/P1 implemented or blocked; safety in code not UI only |
| Security | Credential custody; signed artifacts; TG/web negative auth; injection cannot order |
| Testing | §16 classes pass; binding reqs have verification |
| Broker | Fingerprint; rules verified; recon; stops verified |
| Operations | Runbooks drilled; restore; absence/kill/reimbursement tested |

---

## 8. LIVE eligibility gates (§19)

> LIVE is not a software build flag.

| Gate | Group A condition |
|------|-------------------|
| Capital | RCB ≥ $500 reference floor (necessary, not sufficient) |
| SIM-adequacy | All §4.5 A-SIM-* on frozen strategy |
| Reconciliation | ≥95% clean sessions; no L2+ unresolved in 60d |
| Broker | Exness verified; protective stops confirmed |
| Security & Constitution | Signed artifacts; custody tested |
| Preflight | Every §4.3 item explicit pass |
| Operations | Runbooks; absence; kill drills |

Combined dashboard or Group B state **cannot** satisfy any gate.

---

## 9. Appendix D verification register

Maintain in fact log: assumption, verification method, date, gate blocked if stale. Full table: [COVERAGE-CHECKLIST.md](./COVERAGE-CHECKLIST.md) + source Appendix D.
