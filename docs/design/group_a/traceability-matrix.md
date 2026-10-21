# Group A — Traceability Matrix

Maps **requirement families**, **backlog items**, **operational scenarios**, and **verification classes** to [implementation phases](./implementation-phases.md) and **detailed design files** (see [README.md](./README.md) index). Per-ID listing: [requirements-index.md](./requirements-index.md) (**132** `A-*` IDs). Authoritative wording remains in [`docs/source/SATE_Group_A_System_Documentation.docx`](../../source/SATE_Group_A_System_Documentation.docx) and the [Telegram specification](../../source/SATE_Telegram_Interface_Specification.docx).

| Design doc | Primary requirement families |
|------------|------------------------------|
| [01-system-overview-independence.md](./01-system-overview-independence.md) | A-IND-*, A-PR-* |
| [02-capital-rcb-treasury.md](./02-capital-rcb-treasury.md) | A-RCB-*, A-FEE-*, A-TRE-*, A-OBL-* |
| [03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md) | A-MOD-*, A-SWT-*, A-LAD-*, A-SIM-*, A-CHK-* (with §9) |
| [04-strategy-quant-engine.md](./04-strategy-quant-engine.md) | A-UNI-*, A-SIG-*, A-SZ-*, A-EXE-*, A-PERF-* |
| [05-kernel-oms-reconciliation.md](./05-kernel-oms-reconciliation.md) | A-KRN-*, A-OMS-*, A-REC-* |
| [06-broker-exness-mt5.md](./06-broker-exness-mt5.md) | §7 adapter contract |
| [07-constitution-crypto-deployment.md](./07-constitution-crypto-deployment.md) | A-CON-* |
| [08-halts-kill-checkin.md](./08-halts-kill-checkin.md) | A-KIL-*, A-CHK-*, §9.3 |
| [09-cognitive-plane.md](./09-cognitive-plane.md) | A-COG-* |
| [10-data-audit-fact-log.md](./10-data-audit-fact-log.md) | A-LOG-* |
| [11-web-control-api.md](./11-web-control-api.md) | §13.2–13.3 |
| [telegram-interface.md](./telegram-interface.md) | TG-*, TG-S-*, TG-T-*, TG-PO-*, SEC-*, A-TG-* |
| [12-monitoring-backup-continuity.md](./12-monitoring-backup-continuity.md) | §14 |
| [13-scenarios-runbooks.md](./13-scenarios-runbooks.md) | §15, Appendix C |
| [14-verification-risks-live-gates.md](./14-verification-risks-live-gates.md) | §16–19, §17, INV-* |
| [15-persistent-schemas-constitution.md](./15-persistent-schemas-constitution.md) | Appendix A–B |
| [repository-layout.md](./repository-layout.md) | Repo tree, SoC, CI path filters (Phase 1) |

**Legend:** **Phases 1–27** = implementation phases in [implementation-phases.md](./implementation-phases.md) (build-complete gates). Macro rollup **A–H** in that document maps to phase ranges.

---

## 1. Independence and principles

| ID | Summary | Phase | Source § |
|----|---------|-------|----------|
| A-IND-01 | Capital records scoped to A + broker/account | 2 | 1.3 |
| A-IND-02 | Risk APIs require explicit group scope | 2, 17 | 1.3 |
| A-IND-03 | No cross-group state mutation | 2 | 1.3 |
| A-IND-04 | A operates if B stopped; coupling = reporting + ALL halt | 15, 17 | 1.3, 9.3 |
| A-PR-01 | LLM advisory; numbers trace to tools/deterministic | 21 | 2.4 |
| A-PR-02 | Kernel-only trade credentials | 10 | 2.4 |
| A-PR-03 | Broker source of truth | 13 | 2.4 |
| A-PR-04 | Abstention valid | 20 | 2.4 |
| A-PR-05 | Risk down fast; risk up slow + auth | 17 | 2.4 |
| A-PR-06 | Model change via promotion gates only | 22 | 2.4 |
| A-PR-07 | Risk capital only | 4 | 2.4 |
| A-PR-08 | Journal before action | 20 | 2.4, 12.3 |

---

## 2. Capital, RCB, fees

| ID | Summary | Phase | Source § |
|----|---------|-------|----------|
| A-RCB-01 | Limits on min(RCB, equity) | 4, 6, 9 | 3.4 |
| A-RCB-02 | Equity below RCB shrinks limits | 4, 6 | 3.4 |
| A-RCB-03 | Withdrawal reduces RCB immediately | 4, 6, 23 | 3.4 |
| A-RCB-04 | RCB increase needs ratification | 6, 17 | 3.4 |
| A-RCB-05 | L2+ restarts 14-day cool-off | 6, 9 | 3.4 |
| A-RCB-06 | Deposit during halt inert | 6 | 3.4 |
| A-RCB-07 | Continue on prior RCB if not ratified | 6 | 3.4 |
| A-RCB-08 | No pooling A and B | 2, 4 | 3.4 |
| A-FEE-01–05 | Fees, FX at fill, obligations | 4, 22 | 3.5 |

---

## 3. Modes, switching, SIM adequacy, ladder

| ID | Summary | Phase | Source § |
|----|---------|-------|----------|
| A-MOD-01 | Mode-agnostic strategy | 20 | 4.2 |
| A-MOD-02 | Fingerprint verify | 11 | 4.2 |
| A-MOD-03 | account_mode on all records | 2, 17 | 4.2 |
| A-MOD-04 | UI/Telegram mode badges | 17, 18 | 4.2 |
| A-MOD-05 | No live creds on SIM host path | 10, 19 | 4.2 |
| A-SWT-01–04 | LIVE↔SIM, shadow twin | 15, 26, 27 | 4.4 |
| A-LAD-01–06 | Floor, reverse graduation, ramp | 14, 22, 26, 27 | 4.5 |
| A-SIM-01–08 | SIM-adequacy criteria | 22, 23, 25 | 4.5 |

---

## 4. Strategy and execution

| ID | Summary | Phase | Source § |
|----|---------|-------|----------|
| A-UNI-01–03 | Universe, account type, no overnight bias | 20, 27 | 5.1 |
| A-SIG-01–04 | Kalman, regime, BL, advisory abstain | 20, 21 | 5.2 |
| A-SZ-01–04 | Risk-budget sizing, lot floor | 14, 20 | 5.3 |
| A-EXE-01–04 | Costs, blackout, stops, slippage L1 | 14, 20 | 5.4 |
| A-PERF-01–02 | Net-of-cost benchmark, retirement test | 22 | 5.5 |

---

## 5. Kernel, OMS, reconciliation

| ID | Summary | Phase | Source § |
|----|---------|-------|----------|
| A-KRN-01–08 | Verdict gate, credentials, poll, stops, halt, latency | 9, 10 | 6.3 |
| A-OMS-01–05 | Idempotency, retry rules | 12 | 6.5 |
| A-REC-01–04 | Reconciliation contract | 13 | 6.6 |

---

## 6. Constitution and deployment

| ID | Summary | Phase | Source § |
|----|---------|-------|----------|
| A-CON-01–04 | Signed Constitution, time-lock, no per-trade approval | 7, 8 | 8.1–8.2 |
| §8.3 pipeline | Build, sign, red-team, deploy | 8 | 8.3 |

---

## 7. Halts, kill, check-in

| ID | Summary | Phase | Source § |
|----|---------|-------|----------|
| A-KIL-01–06 | Kill channels, asymmetry, drills | 15, 18 | 9.2 |
| A-CHK-01–05 | Check-in timer in kernel | 16, 23 | 9.4 |
| §9.1 | L1–L4 ladder | 9, 15 | 9.1 |
| §9.3 | HALT_CONFIRMED_* protocol | 15, 17 | 9.3 |

---

## 8. Treasury

| ID | Summary | Phase | Source § |
|----|---------|-------|----------|
| A-TRE-01–06 | Cost tags, allocation, bridge funding | 5, 22, 27 | 10.2 |
| A-OBL-01–03 | Obligations, cross-broker flag | 22, 27 | 10.4 |
| §10.3 | Reimbursement state machine | 5, 22 | 10.3 |

---

## 9. Cognitive plane

| ID | Summary | Phase | Source § |
|----|---------|-------|----------|
| A-COG-01–03 | Zero view default, calibration cap, injection safety | 21 | 11 |
| A-COG-04 | Advisory live gate (**CG-LIVE**; no invented threshold) | 25, 26, 27 | 11 |

---

## 10. Fact log and interfaces

| ID | Summary | Phase | Source § |
|----|---------|-------|----------|
| A-LOG-01–06 | Append-only, hash chain, write failure policy | 3 | 12 |
| A-TG-01–06 | Telegram tagging, allowlist, reduce-only | 18 | 13.4 |
| §13.2 | control-api endpoints | 17 | 13.2 |
| §13.3 | Web pages and reporting label | 17, 22 | 13.3 |

---

## 11. Backlog items (§18)

| ID | Phase | Blocked by |
|----|-------|------------|
| A-P0-01 | 2 | — |
| A-P0-02 | 3 | — |
| A-P0-03 | 2 | — |
| A-P0-04 | 4 | — |
| A-P0-05 | 5 | — |
| A-P0-06 | 6 | — |
| A-P0-07 | 7 | — |
| A-P0-08 | 10 | — |
| A-P0-09 | 9 | — |
| A-P0-10 | 11 | Broker verification → **24** |
| A-P0-11 | 12 | — |
| A-P0-12 | 13 | — |
| A-P0-13 | 14 | — |
| A-P0-14 | 15 | — |
| A-P0-15 | 15 | — |
| A-P0-16 | 17, 18 | — |
| A-P0-17 | 19 | — |
| A-P0-18 | 19 | A-DEC-09 for LIVE |
| A-P0-19 | 8 | — |
| A-P0-20 | 24 | A-DEC-10 |
| A-P0-21 | 14, 24 | **A-DEC-01** |
| A-P1-01 | 22, 23 | A-DEC-03 (hurdle) |
| A-P1-02 | 26, 27 | **A-DEC-02** (L2/L3) |
| A-P1-03 | 26, 27 | — |
| A-P1-04 | 22 | A-DEC-05 |
| A-P1-05 | 22 | — |
| A-P1-06 | 25, 26 | — |
| A-P1-07 | 22 | — |
| A-P2-01 | 27+ | per-module gates |

---

## 12. Open decisions (§20)

| ID | Topic | Blocks | Target phase |
|----|-------|--------|--------------|
| A-DEC-01 | Min lot vs per-trade cap at floor | LIVE gate, A-P0-21 | 24, 25 |
| A-DEC-02 | LIVE-L2/L3 rungs | L2/L3 activation | 27+ |
| A-DEC-03 | SIM return hurdle (6% vs cost-derived) | SIM gate | 22, 23 |
| A-DEC-04 | Constitution time-lock hours | Final Constitution | 7, 25 |
| A-DEC-05 | Shared cost allocation | Treasury | 22 |
| A-DEC-06 | End of funding bridge | Reporting | 22, 27 |
| A-DEC-07 | Windows hosting choice | MT5 host | 11, 19 |
| A-DEC-08 | Emergency relay policy | Production control | 24, 25 |
| A-DEC-09 | Numeric RPO/RTO | LIVE gate | 19, 25 |
| A-DEC-10 | Broker/tax verification | LIVE | 24, 25 |

---

## 13. Invariants (§16.3)

| ID | Phase enforced |
|----|----------------|
| INV-01 | 9+ |
| INV-02 | 2+ |
| INV-03 | 2+ |
| INV-04 | 4+ |
| INV-05 | 5, 22 |
| INV-06 | 15+ |
| INV-07 | 20+ |
| INV-08 | 11, 24, 25 |
| INV-09 | 3+ |
| INV-10 | 3+ |
| INV-11 | 3+ |

---

## 14. Verification classes (§16.1) × phase

| Class | Primary phases |
|-------|----------------|
| UT | 2–4, 9–14, 20 |
| IT | 3, 9–13, 17, 20 |
| BAT | 11, 14, 24 |
| REC | 13, 23 |
| STM | 15, 17, 26, 27 |
| INV, ISO | 2–18 |
| SEC, RT | 8–10, 18, 25 |
| FI | 11, 19 |
| DR, DEP | 8, 19, 25 |
| TRE | 5, 22 |
| HALT | 15, 16, 25, 27 |
| PERF | 9, 14, 20 |
| MOD | 22, 23 |
| OPS | 16, 22, 23, 25–27 |
| TG | 18, 25 |

---

## 15. Operational scenarios (§15) × phase

| Family | IDs | Test phase |
|--------|-----|------------|
| Trading | TS-01 – TS-13 | 12–14, 20, 22 |
| Automatic halts | HL-01, HL-02, HL-07, HL-08, HL-A – HL-F | 13, 15, 25 |
| Owner controls | OC-01 – OC-08 | 15, 18, 25 |
| Account modes | AM-01 – AM-07, AM-A1 – AM-A7 | 17, 23, 26, 27 |
| Capital/treasury | CT-01 – CT-08, CT-A1 | 4–6, 22, 27 |
| Owner presence | OP-01 – OP-06 | 16, 23 |
| Broker/infra | BF-01 – BF-09, BF-A1 – BF-A3 | 11, 19, 27 |
| Model promotion | MP-01 – MP-03 | 20, 22 |

---

## 16. Telegram traceability (spec §11–15)

| ID | Phase |
|----|-------|
| TG-01 – TG-16 | 18 (core), 22, 25–27 (digest, /why) |
| TG-S-01 – TG-S-25 | 18, 22, 25–27 (by scenario) |
| TG-T-01 – TG-T-15 | 18, 25 |
| TG-PO-01 – TG-PO-10 | 18 |
| TG-PO-11 – TG-PO-15 | 18, 25 |
| OI-TG-01 – OI-TG-06 | 18, 25–26 (decisions) |

---

## 17. Appendix D assumptions × phase

| Assumption | Verify by | Blocks | Phase |
|------------|-----------|--------|-------|
| Exness Kenya eligibility, products | Broker docs | LIVE | 24, 25 |
| MT5 Python terms, VPS | Exness terms | MT5 host | 11, 19 |
| Contract specs / min lot | Broker specs | A-DEC-01 | 11, 14 |
| Protective order behaviour | Tests | LIVE | 14, 24, 25 |
| Windows hosting cost | Providers | MT5 host | 19 |
| Latency/slippage | SIM measurement | SIM ops | 11, 20, 23 |
| Kenya tax CFD/FX | Tax professional | LIVE | 24, 25 |
| Programmatic withdrawal | Broker docs | Treasury | 23, 27 (manual assumed) |
| Email provider | Test send | Check-in | 16 |
| Data/news licences | Vendor | Infra | 19, 20 |

---

## 18. Runbooks (Appendix C) × phase

| Runbook | Drill phase |
|---------|-------------|
| C.1 Kill switch | 15, 25, 27 |
| C.2 Kernel heartbeat | 19, 25 |
| C.3 Reconciliation mismatch | 13, 23 |
| C.4 SIM → LIVE | 25, 26 |
| C.5 Recovery L3/L4 | 25, 27 |
| C.6 Check-in lapsed | 16, 23 |
| C.7 Broker failure | 23, 27 |
| C.8 Manual withdrawal | 23, 27 |
| C.9 Reverse graduation | 23, 27 |
| C.10 MT5 terminal crash | 11, 19 |
