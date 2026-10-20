# Group A — Traceability Matrix

Maps **requirement families**, **backlog items**, **operational scenarios**, and **verification classes** to [implementation phases](./implementation-phases.md). Authoritative wording remains in [`docs/source/SATE_Group_A_System_Documentation.docx`](../../source/SATE_Group_A_System_Documentation.docx) and the [Telegram specification](../../source/SATE_Telegram_Interface_Specification.docx).

**Legend:** P0–P7 = implementation phases in `implementation-phases.md`.

---

## 1. Independence and principles

| ID | Summary | Phase | Source § |
|----|---------|-------|----------|
| A-IND-01 | Capital records scoped to A + broker/account | P1 | 1.3 |
| A-IND-02 | Risk APIs require explicit group scope | P1, P3 | 1.3 |
| A-IND-03 | No cross-group state mutation | P1 | 1.3 |
| A-IND-04 | A operates if B stopped; coupling = reporting + ALL halt | P3 | 1.3, 9.3 |
| A-PR-01 | LLM advisory; numbers trace to tools/deterministic | P4 | 2.4 |
| A-PR-02 | Kernel-only trade credentials | P2 | 2.4 |
| A-PR-03 | Broker source of truth | P2 | 2.4 |
| A-PR-04 | Abstention valid | P4 | 2.4 |
| A-PR-05 | Risk down fast; risk up slow + auth | P3 | 2.4 |
| A-PR-06 | Model change via promotion gates only | P4, P5 | 2.4 |
| A-PR-07 | Risk capital only | P1 | 2.4 |
| A-PR-08 | Journal before action | P4 | 2.4, 12.3 |

---

## 2. Capital, RCB, fees

| ID | Summary | Phase | Source § |
|----|---------|-------|----------|
| A-RCB-01 | Limits on min(RCB, equity) | P1, P2 | 3.4 |
| A-RCB-02 | Equity below RCB shrinks limits | P1 | 3.4 |
| A-RCB-03 | Withdrawal reduces RCB immediately | P1, P5 | 3.4 |
| A-RCB-04 | RCB increase needs ratification | P1, P3 | 3.4 |
| A-RCB-05 | L2+ restarts 14-day cool-off | P1, P2 | 3.4 |
| A-RCB-06 | Deposit during halt inert | P1 | 3.4 |
| A-RCB-07 | Continue on prior RCB if not ratified | P1 | 3.4 |
| A-RCB-08 | No pooling A and B | P1 | 3.4 |
| A-FEE-01–05 | Fees, FX at fill, obligations | P1, P5 | 3.5 |

---

## 3. Modes, switching, SIM adequacy, ladder

| ID | Summary | Phase | Source § |
|----|---------|-------|----------|
| A-MOD-01 | Mode-agnostic strategy | P4 | 4.2 |
| A-MOD-02 | Fingerprint verify | P2 | 4.2 |
| A-MOD-03 | account_mode on all records | P1, P3 | 4.2 |
| A-MOD-04 | UI/Telegram mode badges | P3 | 4.2 |
| A-MOD-05 | No live creds on SIM host path | P2, P3 | 4.2 |
| A-SWT-01–04 | LIVE↔SIM, shadow twin | P3, P7 | 4.4 |
| A-LAD-01–06 | Floor, reverse graduation, ramp | P2, P5, P7 | 4.5 |
| A-SIM-01–08 | SIM-adequacy criteria | P5, P6 | 4.5 |

---

## 4. Strategy and execution

| ID | Summary | Phase | Source § |
|----|---------|-------|----------|
| A-UNI-01–03 | Universe, account type, no overnight bias | P4, P7 | 5.1 |
| A-SIG-01–04 | Kalman, regime, BL, advisory abstain | P4 | 5.2 |
| A-SZ-01–04 | Risk-budget sizing, lot floor | P2, P4 | 5.3 |
| A-EXE-01–04 | Costs, blackout, stops, slippage L1 | P2, P4 | 5.4 |
| A-PERF-01–02 | Net-of-cost benchmark, retirement test | P5 | 5.5 |

---

## 5. Kernel, OMS, reconciliation

| ID | Summary | Phase | Source § |
|----|---------|-------|----------|
| A-KRN-01–08 | Verdict gate, credentials, poll, stops, halt, latency | P2 | 6.3 |
| A-OMS-01–05 | Idempotency, retry rules | P2 | 6.5 |
| A-REC-01–04 | Reconciliation contract | P2 | 6.6 |

---

## 6. Constitution and deployment

| ID | Summary | Phase | Source § |
|----|---------|-------|----------|
| A-CON-01–04 | Signed Constitution, time-lock, no per-trade approval | P1, P3 | 8.1–8.2 |
| §8.3 pipeline | Build, sign, red-team, deploy | P3 | 8.3 |

---

## 7. Halts, kill, check-in

| ID | Summary | Phase | Source § |
|----|---------|-------|----------|
| A-KIL-01–06 | Kill channels, asymmetry, drills | P3 | 9.2 |
| A-CHK-01–05 | Check-in timer in kernel | P3, P5 | 9.4 |
| §9.1 | L1–L4 ladder | P2, P3 | 9.1 |
| §9.3 | HALT_CONFIRMED_* protocol | P3 | 9.3 |

---

## 8. Treasury

| ID | Summary | Phase | Source § |
|----|---------|-------|----------|
| A-TRE-01–06 | Cost tags, allocation, bridge funding | P1, P5 | 10.2 |
| A-OBL-01–03 | Obligations, cross-broker flag | P5, P7 | 10.4 |
| §10.3 | Reimbursement state machine | P1, P5 | 10.3 |

---

## 9. Cognitive plane

| ID | Summary | Phase | Source § |
|----|---------|-------|----------|
| A-COG-01–03 | Zero view default, calibration cap, injection safety | P4 | 11 |
| A-COG-04 | Advisory live gate (no invented threshold) | P6, P7 | 11 |

---

## 10. Fact log and interfaces

| ID | Summary | Phase | Source § |
|----|---------|-------|----------|
| A-LOG-01–06 | Append-only, hash chain, write failure policy | P1 | 12 |
| A-TG-01–06 | Telegram tagging, allowlist, reduce-only | P3 | 13.4 |
| §13.2 | control-api endpoints | P3 | 13.2 |
| §13.3 | Web pages and reporting label | P3, P5 | 13.3 |

---

## 11. Backlog items (§18)

| ID | Phase | Blocked by |
|----|-------|------------|
| A-P0-01 | P1 | — |
| A-P0-02 | P1 | — |
| A-P0-03 | P1 | — |
| A-P0-04 | P1 | — |
| A-P0-05 | P1 | — |
| A-P0-06 | P1 | — |
| A-P0-07 | P1 | — |
| A-P0-08 | P2 | — |
| A-P0-09 | P2 | — |
| A-P0-10 | P2 | Broker verification (ongoing) |
| A-P0-11 | P2 | — |
| A-P0-12 | P2 | — |
| A-P0-13 | P2 | — |
| A-P0-14 | P3 | — |
| A-P0-15 | P3 | — |
| A-P0-16 | P3 | — |
| A-P0-17 | P3 | — |
| A-P0-18 | P3 | A-DEC-09 for LIVE |
| A-P0-19 | P3 | — |
| A-P0-20 | P3, P6 | A-DEC-10 |
| A-P0-21 | P2, P6 | **A-DEC-01** |
| A-P1-01 | P5 | A-DEC-03 (hurdle) |
| A-P1-02 | P7 | **A-DEC-02** (L2/L3) |
| A-P1-03 | P7 | — |
| A-P1-04 | P5 | A-DEC-05 |
| A-P1-05 | P5 | — |
| A-P1-06 | P6, P7 | — |
| A-P1-07 | P5 | — |
| A-P2-01 | Post-L1 | per-module gates |

---

## 12. Open decisions (§20)

| ID | Topic | Blocks | Target phase |
|----|-------|--------|--------------|
| A-DEC-01 | Min lot vs per-trade cap at floor | LIVE gate, A-P0-21 | P6 |
| A-DEC-02 | LIVE-L2/L3 rungs | L2/L3 activation | P7+ |
| A-DEC-03 | SIM return hurdle (6% vs cost-derived) | SIM gate | P5 |
| A-DEC-04 | Constitution time-lock hours | Final Constitution | P6 |
| A-DEC-05 | Shared cost allocation | Treasury | P5 |
| A-DEC-06 | End of funding bridge | Reporting | P5 |
| A-DEC-07 | Windows hosting choice | Phase 3 hosting | P3 |
| A-DEC-08 | Emergency relay policy | Production control | P6 |
| A-DEC-09 | Numeric RPO/RTO | LIVE gate | P6 |
| A-DEC-10 | Broker/tax verification | LIVE | P6 |

---

## 13. Invariants (§16.3)

| ID | Phase enforced |
|----|----------------|
| INV-01 | P2+ |
| INV-02 | P1+ |
| INV-03 | P1+ |
| INV-04 | P1+ |
| INV-05 | P1, P5 |
| INV-06 | P3+ |
| INV-07 | P4+ |
| INV-08 | P2, P6 |
| INV-09 | P1+ |
| INV-10 | P1+ |
| INV-11 | P1+ |

---

## 14. Verification classes (§16.1) × phase

| Class | Primary phases |
|-------|----------------|
| UT | P1, P2, P4 |
| IT | P1, P2, P4 |
| BAT | P2, P6 |
| REC | P2, P5 |
| STM | P2, P3, P7 |
| INV, ISO | P1–P3 |
| SEC, RT | P2, P3, P6 |
| FI | P2, P3 |
| DR, DEP | P3, P6 |
| TRE | P1, P5 |
| HALT | P3, P6 |
| PERF | P2, P4 |
| MOD | P5 |
| OPS | P3, P5, P6 |
| TG | P3, P6 |

---

## 15. Operational scenarios (§15) × phase

| Family | IDs | Test phase |
|--------|-----|------------|
| Trading | TS-01 – TS-13 | P2, P4 |
| Automatic halts | HL-01, HL-02, HL-07, HL-08, HL-A – HL-F | P2, P3 |
| Owner controls | OC-01 – OC-08 | P3, P6 |
| Account modes | AM-01 – AM-07, AM-A1 – AM-A7 | P3, P5, P7 |
| Capital/treasury | CT-01 – CT-08, CT-A1 | P1, P5, P7 |
| Owner presence | OP-01 – OP-06 | P3, P5 |
| Broker/infra | BF-01 – BF-09, BF-A1 – BF-A3 | P2, P3, P7 |
| Model promotion | MP-01 – MP-03 | P5 |

---

## 16. Telegram traceability (spec §11–15)

| ID | Phase |
|----|-------|
| TG-01 – TG-16 | P3 (core), P5–P7 (/why, digest) |
| TG-S-01 – TG-S-25 | P3–P7 (by scenario) |
| TG-T-01 – TG-T-15 | P3, P6 |
| TG-PO-01 – TG-PO-10 | P3 |
| TG-PO-11 – TG-PO-15 | P5–P7 |
| OI-TG-01 – OI-TG-06 | P3, P6 (decisions) |

---

## 17. Appendix D assumptions × phase

| Assumption | Verify by | Blocks | Phase |
|------------|-----------|--------|-------|
| Exness Kenya eligibility, products | Broker docs | Phase 4 / LIVE | P6 |
| MT5 Python terms, VPS | Exness terms | Phase 3 | P3 |
| Contract specs / min lot | Broker specs | A-DEC-01 | P2 |
| Protective order behaviour | Tests | Phase 4 / LIVE | P6 |
| Windows hosting cost | Providers | Phase 3 | P3 |
| Latency/slippage | SIM measurement | Phases 2–3 | P2–P3 |
| Kenya tax CFD/FX | Tax professional | Phase 4 | P6 |
| Programmatic withdrawal | Broker docs | Phase 5 | P5 (manual assumed) |
| Email provider | Test send | Phase 1 | P1 |
| Data/news licences | Vendor | Phase 3 | P3 |

---

## 18. Runbooks (Appendix C) × phase

| Runbook | Drill phase |
|---------|-------------|
| C.1 Kill switch | P3, P6 |
| C.2 Kernel heartbeat | P3 |
| C.3 Reconciliation mismatch | P2, P5 |
| C.4 SIM → LIVE | P6, P7 |
| C.5 Recovery L3/L4 | P6 |
| C.6 Check-in lapsed | P3, P5 |
| C.7 Broker failure | P5, P7 |
| C.8 Manual withdrawal | P5, P7 |
| C.9 Reverse graduation | P5, P7 |
| C.10 MT5 terminal crash | P2, P3 |
