# Group A — Implementation Phases (Design)

**Purpose:** Comprehensive phased plan to implement Group A from zero through **LIVE eligibility** and **LIVE-L1** operation, with deliverables, acceptance criteria, verification, and pointers to every major section of the authoritative system documentation.

**Sources:**

- [`docs/source/SATE_Group_A_System_Documentation.docx`](../../source/SATE_Group_A_System_Documentation.docx) — §1–20, Appendices A–D
- [`docs/source/SATE_Telegram_Interface_Specification.docx`](../../source/SATE_Telegram_Interface_Specification.docx) — §0–18
- [independent-deployment-strategy.md](./independent-deployment-strategy.md)
- [architecture-components.md](./architecture-components.md)
- [traceability-matrix.md](./traceability-matrix.md)

**Critical rule (§1.4):** Gaps marked **IMPLEMENTATION BLOCKER — DECISION REQUIRED** in §20 shall not be filled by engineering assumption. Track in `decision-log.md`.

---

## Phase 0 — Governance, traceability, and environment

**Maps to:** Group A §18.1 step 1; §1.4–1.5; §20; §16.1 (test hierarchy definition).

### Objectives

- Establish requirement traceability from **A-*** IDs, **A-P0/P1/P2** backlog, scenarios §15, and Telegram **TG-*** families to work items.
- Stand up monorepo layout, CI, secret handling, and pinned toolchains for reproducible kernel builds (**§8.3**).

### Deliverables

| ID | Deliverable | Acceptance |
|----|-------------|------------|
| D0-1 | Requirements index imported from source (IDs unchanged) | Every §1–20 section referenced in traceability matrix |
| D0-2 | Decision log with **A-DEC-01–10** status | Blockers visible; no silent defaults |
| D0-3 | Architecture decision record (ADR) for A-only deployment | Matches [independent-deployment-strategy.md](./independent-deployment-strategy.md) |
| D0-4 | CI pipeline skeleton | Runs unit tests; kernel build job stub |
| D0-5 | Threat model draft (control plane, Telegram, kernel) | Covers R-18, R-85, Telegram TG-S-15 |

### Verification

- Review checklist: **§17.1** design review items 6–7 (assumption register, two-system consistency — B absent case documented).

### Appendix D (early)

| Dependency | Phase gate |
|------------|------------|
| Email provider for check-in reminders (independent of Telegram) | **Phase 1** deploy |

---

## Phase 1 — Platform core (fact log, capital, RCB, Constitution)

**Maps to:** §3 (Capital), §8.1–8.2 (Constitution), §12 (Fact log), §10.1–10.2 (treasury foundations); backlog **A-P0-01–07**, **A-P0-04–06**.

### Objectives

- Immutable **Group A data domain** with no shared mutable cross-group risk state (**A-P0-03**, **A-IND-01–02**).
- Append-only **hash-chained fact log** (**A-LOG-01–06**).
- **Five-state capital ledger** distinct types (**§3.1**, **A-P0-04**): equity, realised PnL, settled, reserved, withdrawable — **INV-04**.
- **RCB service** with 14-day ratification and cool-off rules (**A-RCB-01–08**).
- **Constitution** schema, sign, verify (**A-CON-01–04**, **A-P0-07**); load example structure **Appendix A**.

### Deliverables

| Backlog | Component | Key requirements |
|---------|-----------|------------------|
| A-P0-01 | Account identity registry | A-SIM, A-LIVE profiles; fingerprint fields **§4.2** |
| A-P0-02 | Fact log | Event classes **§12.1**; chain **A-LOG-05** |
| A-P0-03 | Isolated A store | **A-IND-***, **INV-02** |
| A-P0-04 | Capital ledger | **A-FEE-01–05** where applicable |
| A-P0-05 | Reimbursement-owed ledger | **§10.1**, **INV-05** |
| A-P0-06 | RCB service | Ratify via web passkey **§4.3** checklist |
| A-P0-07 | Constitution tooling | Emergency tighten only **§8.2** |

### Verification (§16.1)

| Class | Focus |
|-------|--------|
| **UT** | Capital math, RCB transitions, schema validation |
| **IT** | Fact log write → projection read |
| **TRE** | Reimbursement state stubs (**§10.3**) |
| **SEC** | Constitution signature rejection |

### Exit gate

- All **A-P0-01–07** acceptance columns satisfied in SIM/mock broker environment.
- **ISO** tests started: reject Group B capital in A APIs (**§1.3** table).

---

## Phase 2 — Safety kernel, OMS, Exness MT5 adapter

**Maps to:** §6 (Trading engine), §7 (Broker), §5.4 (protection); **A-P0-08–13**, **A-P0-11–12**.

### Objectives

- **KERNEL-A** as sole credential holder (**A-KRN-02**, **A-PR-02**).
- Full **intent → verdict → order** path (**§6.1**) with check order **§6.4**.
- **MT5 bridge** + adapter state model **§7.2–7.3**.
- **Idempotent OMS** (**A-OMS-01–05**) and **reconciliation** (**A-REC-01–04**).
- **Protective stop** verification (**A-EXE-03**, **A-P0-13**).

### Deliverables

| Backlog | Deliverable |
|---------|-------------|
| A-P0-08 | Credential vault interface inside kernel only |
| A-P0-09 | Kernel verdict engine + persistence of halt state **A-KRN-05** |
| A-P0-10 | MT5 adapter + ZeroMQ bridge |
| A-P0-11 | Order lifecycle + client correlation IDs |
| A-P0-12 | Reconciliation engine (event + 5s poll **A-KRN-03**) |
| A-P0-13 | Protective-stop gate (no entry without stop) |

### Scenario coverage (§15.1)

Implement automated or manual tests for **TS-01** through **TS-13** (entries, rejects, partial fill, stale data, duplicate intent, stop failure).

### Verification (§16.1)

| Class | Focus |
|-------|--------|
| **BAT** | Adapter contract **§7.1** |
| **REC** | Mismatch detection **HL-B** |
| **RT** | Wrong account **HL-C**, oversized order |
| **FI** | Bridge disconnect **BF-A1** |
| **PERF** | Kernel latency **A-KRN-07** (shadow measurement) |

### Appendix D

| Item | Note |
|------|------|
| Latency/slippage | Measure in SIM — **Phases 2 and 3** |

### Exit gate

- **INV-01** enforced: no order without verdict.
- Red-team subset **§16.2** (wrong terminal, MT5 disconnect) passing in SIM.

### Blocker

- **A-P0-21** / **A-DEC-01**: minimum-lot vs per-trade cap at $500 — **BLOCKED** until owner decision (**§4.5** callout). Implement rejection path **`untradeable_at_this_capital`** (**TS-04**) regardless.

---

## Phase 3 — Halt/kill, control plane, monitoring, Windows host

**Maps to:** §9 (Halts/kill/check-in), §13 (Web/Telegram), §14 (Monitoring/backup); **A-P0-14–20**, **A-P0-16–18**; Telegram spec §0–15.

### Objectives

- Halt ladder **L1–L4** (**§9.1**) and owner kill **K1–K3** (**§9.2**) with scope **A** default.
- **Global halt protocol** with partial confirmation when B absent (**§9.3**, **INV-06**).
- **control-api** + web SPA (**§13.2–13.3**); passkey for risk-increasing paths.
- **notifier-bot** reduce-only (**Telegram spec §0** principles 1–6).
- Monitoring, CRITICAL alert path (**§14.1**), encrypted backup (**§14.2**, **A-P0-18**).
- **Windows host** decision **A-DEC-07** and provisioning (**Appendix D** Phase 3).

### Deliverables

| Backlog | Deliverable | Telegram / other |
|---------|-------------|------------------|
| A-P0-14 | Halt/kill state machine + coordinator | TG-PO-06, TG-PO-07; **TG-S-08–10** |
| A-P0-15 | Mode state machine SIM/LIVE-L1/MANAGE_ONLY/HALTED | **AM-01–07** |
| A-P0-16 | Scope enforcement on all control APIs | **A-IND-02**, ISO tests |
| A-P0-17 | Monitoring + alerting | **§14.1** severity rules |
| A-P0-18 | Backup/restore runbook + monthly drill | **DR** tests |
| A-P0-19 | Kernel sign/deploy pipeline + frozen red-team suite | **DEP** tests |
| A-P0-20 | Broker/account verification **package** (evidence store) | **§7.4**, **A-DEC-10** in progress |

**Telegram P0 backlog (apply to Group A):** **TG-PO-01** through **TG-PO-10** (Telegram spec §15) — bot skeleton, keyboard, notifications, confirm buttons, control-api integration, fact-log stream.

### Check-in (§9.4)

- Kernel timer **A-CHK-03**; `/alive` **A-CHK-01**; away mode completes in web **A-CHK-02**.
- Email reminders (Appendix D Phase 1 provider).

### Verification (§16.1)

| Class | Focus |
|-------|--------|
| **HALT** | **OC-01–08**, **HL-01–HL-F**, partial ALL **OC-04** |
| **TG** | **TG-T-01–15** (Telegram spec §14) |
| **OPS** | Kill drills **A-KIL-06** |
| **DR** | Restore + hash chain **§14.2** |

### Appendix D (Phase 3)

- Exness MT5 Python integration terms
- Windows hosting options/pricing
- Market-data/news licence terms

### Exit gate

- **A-KIL-02** verified: Telegram cannot resume or arm LIVE (**TG-T-07**).
- **A-DEC-07** recorded (VPS vs owned PC vs broker VPS).
- Production control plane blocked on **A-DEC-08** (emergency relay) and **A-DEC-09** (numeric RPO/RTO) unless explicitly waived for SIM-only with LIVE gate still closed (**§14.2**).

---

## Phase 4 — Strategy, sizing, and cognitive plane (SIM)

**Maps to:** §5 (Strategy), §11 (Cognitive), §6.2 (Intent); operating principles **A-PR-01**, **A-PR-04**, **A-PR-06**.

### Objectives

- Mode-agnostic strategy code producing **Intents** (**A-MOD-01**).
- Kalman (**A-SIG-01**), regime (**A-SIG-02**), Black-Litterman (**A-SIG-03–04**).
- Risk-budget sizing **§5.3** (**A-SZ-01–04**).
- Cost model and guards: swap, news blackout, slippage budget **A-EXE-01–04**.
- Cognitive plane integration: **AdvisorySignal** schema **§11**; invalid ⇒ zero view (**A-COG-01–03**).
- Decision journal **§12.3** before action.

### Deliverables

| Area | Deliverable |
|------|-------------|
| Universe | Constitution-driven; LIVE-L1 EUR/USD only **A-UNI-01** |
| Data | Tick ingestion with freshness metadata **§6.7** |
| Backtest | Vectorised, full cost model; no LLM in loop **§5.5** |
| Live SIM loop | Continuous FX week **§2.3** timing |
| Advisory | Signed signals; abstain paths **§15.1 TS-02–03** |

### Scenario coverage

**TS-01–11**, **MP-01–03** (champion/challenger infrastructure only — promotion gates live but no live promotion without evidence).

### Verification

| Class | Focus |
|-------|--------|
| **UT** | Sizing floor, lot step down-round **A-SZ-02** |
| **MOD** | Challenger interface **§15.8** (no threshold invention for advisory live **A-COG-04**) |
| **IT** | Intent schema **§6.2** |

### Exit gate

- SIM generates intents, kernel approves/rejects, orders on **demo** account with protective stops.
- Stale feed blocks new risk (**TS-10**).

---

## Phase 5 — SIM evidence, adequacy engine, and operational maturity

**Maps to:** §4.5 (**A-SIM-01–08**, **A-LAD-01–06**); backlog **A-P1-01**, **A-P1-04–05**, **A-P1-07**; §15 (operational scenarios); §17 (risks).

### Objectives

- Run **≥ 6 months** SIM at reference floor sizing (**A-SIM-01**) — calendar gate, not software gate.
- **SIM-adequacy engine** computes evidence: Sharpe **A-SIM-03**, return hurdle **A-SIM-04** (pending **A-DEC-03**), trades/bootstrap **A-SIM-05**, reconciliation **A-SIM-02**, halts **A-SIM-06**, frozen params **A-SIM-07**, floor-scale sizing **A-SIM-08**.
- **Cost allocation** and reimbursement audibility (**A-P1-04**, **A-TRE-02**, **A-DEC-05**).
- **Champion/challenger** shadow machinery (**A-P1-05**, **§15.8**) — Kalman tuning frozen last 3 months of SIM **A-SIM-07**.
- **Performance reporting** net-of-cost vs benchmark **A-PERF-01–02**.

### Deliverables

| Backlog | Deliverable |
|---------|-------------|
| A-P1-01 | SIM-adequacy evidence store + reproducible gate report |
| A-P1-04 | Cost allocation events + treasury integration |
| A-P1-05 | Promotion gate runner (shadow only until criteria met) |
| A-P1-07 | Dashboard performance views (SIM separate from LIVE **A-MOD-03**) |

### Drills (§16.1 **OPS**, Appendix C)

Execute and document: **C.2** heartbeat lost, **C.3** reconciliation mismatch, **C.6** check-in lapsed (SIM path **OP-05**), **C.10** MT5 crash, reverse graduation **C.9** / **AM-A5**.

### Verification (§16.2)

- Minimum-lot sizing test
- Reverse graduation drill
- Ramp clock independence (30-day vs 90-day) — prepare for Phase 7

### Exit gate

- SIM-adequacy report shows pass/fail per criterion with stored evidence (**§19** SIM-adequacy gate).
- **95%** reconciliation clean rate trajectory (**A-SIM-02**).
- No unresolved **L2+** in last 60 days (**A-SIM-06**).

### Blockers

- **A-DEC-03** blocks final SIM gate if hurdle undefined.
- **A-P1-02** L2/L3 ladder **blocked on A-DEC-02** — implement L1↔SIM only.

---

## Phase 6 — LIVE readiness (preflight, security, compliance)

**Maps to:** §4.3–4.4, §19 (Definition of Done), §16 (full suite), §18.1 steps 12–14; **A-P1-06**; Appendix D Phase 4.

### Objectives

- **LIVE preflight engine** with explicit reason codes (**A-P1-06**, **AM-03**).
- Complete **§19** “Complete when” for Architecture, Code, Security, Testing, Broker, Operations.
- **Broker verification** written evidence (**§7.4**, **A-DEC-10**): Kenya-resident Exness, account type, leverage, products, protective orders, withdrawals.
- **Tax/reporting** verification (**A-FEE-05**, Appendix D).
- Resolve or formally defer blockers: **A-DEC-01**, **A-DEC-04**, **A-DEC-08**, **A-DEC-09**.
- Execute full **P0** test suite + **§17.1** design review at gate.

### LIVE eligibility gates (§19 table)

| Gate | Implementation evidence |
|------|-------------------------|
| Capital | RCB ≥ $500 reference floor (**§3.3**) — necessary, not sufficient |
| SIM-adequacy | §4.5 all **A-SIM-*** |
| Reconciliation | 95% clean; no L2+ in 60 days |
| Broker | Exness verified + stops confirmed |
| Security & Constitution | Signed artifacts; credential custody tests |
| Preflight | All **§4.3** checklist items |
| Operations | Runbooks drilled; owner-absence; kill |

### Verification

Run full **§16.1** class list where applicable; all **INV-01–INV-11**; **TG-T-*** suite; Group A **§16.2** specific tests.

### Exit gate

- Owner can arm LIVE via web (**§4.3**) but switch remains blocked until Phase 7 confirmation and **A-DEC-01** resolved for ramp economics.
- **A-DEC-09**: numeric RPO/RTO set or LIVE remains blocked (**§14.2**).

---

## Phase 7 — LIVE-L1 entry, ramp, shadow twin, and steady state

**Maps to:** §4.1 LIVE-L1, §4.5 ramp/ladder, **A-P1-02–03**; scenarios **AM-01**, **AM-A1–A7**; **A-SWT-03–04**.

### Objectives

- Execute SIM→LIVE procedure: arming 24h → Telegram code → web confirm → safe window → **ramp 0.25×**, **30-day minimum** (**§4.3**, Appendix A).
- **Shadow twin**: parallel SIM intents while LIVE (**A-SWT-03**, **A-P1-03**).
- **Reverse graduation** and floor rules live (**A-LAD-01–06**).
- **LIVE-L2/L3**: implement code paths but keep disabled until **A-DEC-02**.
- Steady-state monitoring, treasury payouts **§10.5**, manual withdrawals Appendix **C.8**.

### Deliverables

| Backlog | Deliverable |
|---------|-------------|
| A-P1-02 | L1 ladder + reverse graduation (L2/L3 gated) |
| A-P1-03 | Divergence reports (slippage, rejections) |
| A-P1-06 | Production preflight on each arm attempt |

### Scenario coverage

**AM-01–07**, **AM-A1–A7**, **OC-07–08**, treasury **CT-05**, broker **BF-01–BF-A3**.

### Advisory live use

**A-COG-04**: Phase 6 cognitive gate — do not enable advisory live contribution without approved validation methodology (no invented threshold).

### P2 backlog (post-L1)

**A-P2-01**: Research modules (triangular arb, wavelet, RL execution) — **§5.5**; each behind its own gate; default **off**.

### Exit gate (steady LIVE-L1)

- LIVE-L1 operating under Constitution limits with shadow twin reporting.
- Ramp clock and 90-day evidence clock tracked independently (**§4.5**).
- Incident response proven: at least one simulated **L2** recovery (**HL-B**) and kill **K2** drill in LIVE or staged live account.

---

## Cross-phase backlog summary (Group A §18)

| Priority | Items | Phase |
|----------|-------|-------|
| P0 | A-P0-01 – A-P0-20 | 1–3 |
| BLOCKED | A-P0-21 (A-DEC-01) | 2/6 |
| P1 | A-P1-01 – A-P1-07 | 4–7 |
| P2 | A-P2-01 | After LIVE-L1 stable |

**Telegram:** TG-PO-01 – TG-PO-15 (P0/P1 per Telegram spec §15) — primarily Phase 3, with P1 items in Phase 5–7.

---

## Cognitive plane “Phase 6 gate” (§11)

Distinct from implementation Phase 6 above: **A-COG-04** references an internal **validation gate** before advisory signals influence LIVE economics. Implementation plan:

1. Phases 4–5: advisory connected in **shadow**; evaluate rank correlation, calibration, P&L contribution.
2. Phase 6 LIVE readiness: document pass/fail criteria (owner decision — no engineering invention).
3. Phase 7: if gate not passed, operate LIVE with **zero advisory view** (**A-COG-01**) — fully valid.

---

## Definition of Done (Group A §19)

LIVE is **not** a build flag. Phase 7 completes implementation; **LIVE eligibility** is a **evidence predicate** evaluated by preflight (**§4.3**, **§19**).

“Done” for the **program** means:

1. All P0 and P1 items implemented or explicitly blocked with owner acceptance.
2. Every **§16.1** test class executed at the required phase gate.
3. **§17.1** design review completed at LIVE gate.
4. Runbooks **Appendix C** versioned and drilled.
5. Owner can operate Group A independently while Group B is undeployed (**A-IND-04**).

---

## Document section index (quick reference)

| Topic | Group A § |
|-------|-----------|
| Independence | 1.3, 3 callout |
| Objectives / characteristics | 2.1–2.3 |
| Operating principles | 2.4 (A-PR-*) |
| Shared services | 2.6 |
| Capital / RCB | 3, A-RCB-*, A-FEE-* |
| Modes / SIM adequacy / ladder | 4, A-MOD-*, A-SIM-*, A-LAD-* |
| Strategy | 5, A-UNI-*, A-SIG-*, A-SZ-*, A-EXE-*, A-PERF-* |
| Kernel / OMS / recon | 6, A-KRN-*, A-OMS-*, A-REC-* |
| Broker | 7 |
| Constitution / deploy | 8, A-CON-* |
| Halts / kill / check-in | 9, A-KIL-*, A-CHK-* |
| Treasury | 10, A-TRE-*, A-OBL-* |
| Cognitive | 11, A-COG-* |
| Fact log | 12, A-LOG-* |
| Web / Telegram summary | 13, A-TG-* |
| Monitoring / backup | 14 |
| Scenarios | 15 |
| Verification | 16, INV-* |
| Risks | 17 |
| Backlog | 18, A-P0/P1/P2-* |
| LIVE eligibility | 19 |
| Decisions | 20, A-DEC-* |
| Constitution example | Appendix A |
| Entities | Appendix B |
| Runbooks | Appendix C |
| Assumptions | Appendix D |

| Topic | Telegram spec § |
|-------|-----------------|
| Principles / scope | 0–1 |
| Taxonomy | 2 |
| UX flows | 3–8 |
| Notifications | 6 |
| Security / state machine | 9–10 |
| Requirements / tests / backlog | 11–15 |
| DoD | 16 |
