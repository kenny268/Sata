# Group A — Implementation Phases (Design)

**Purpose:** Production-grade phased delivery plan for Group A from zero through **LIVE-L1 steady state**. Each phase is a **build-complete gate**: every component, contract, test, and operational artifact in scope for that phase shall be **implemented, integrated, verified, and documented** before exit—not stubbed, not “TODO in production,” not deferred without an explicit **BLOCKED** decision in [decision-log.md](./decision-log.md).

**Scale bar:** Treat each phase as suitable for a **regulated, high-availability trading platform** (clear ownership, rollback, evidence, runbooks, security negative tests, and audit replay).

**Sources (normative):**

- [`docs/source/SATE_Group_A_System_Documentation.docx`](../../source/SATE_Group_A_System_Documentation.docx) — §1–20, Appendices A–D
- [`docs/source/SATE_Telegram_Interface_Specification.docx`](../../source/SATE_Telegram_Interface_Specification.docx) — §0–18
- Subsystem design: [README.md](./README.md) index
- Deployment: [independent-deployment-strategy.md](./independent-deployment-strategy.md)

**Critical rule (§1.4):** **IMPLEMENTATION BLOCKER — DECISION REQUIRED** items (**§20**, **OI-TG-***) shall not be silently defaulted. Track in [decision-log.md](./decision-log.md) and [SOURCE-AMBIGUITIES.md](./SOURCE-AMBIGUITIES.md).

**Naming:** **Implementation Phase 1–27** below. **A-COG-04 “Phase 6 gate”** in §11 is a **cognitive validation gate** (label **CG-LIVE** in this doc)—not Implementation Phase 6.

---

## How to read this document

| Section per phase | Meaning |
|-------------------|---------|
| **Prerequisites** | Prior phases must have passed **exit criteria** |
| **Build scope** | Services, binaries, schemas, infra, and UI that must exist and run |
| **Requirements** | Binding **A-*** / **TG-*** IDs implemented in this phase |
| **Backlog** | **A-P0/P1/P2**, **TG-PO-***, mapped from §18 |
| **Verification** | §16.1 classes and §15 scenarios that must pass to exit |
| **Exit criteria** | Objective “done” for the phase; no partial credit |

### Macro stages (executive rollup)

| Macro | Implementation phases | Theme |
|-------|----------------------|--------|
| **A** | 1–3 | Governance, identity, audit |
| **B** | 4–7 | Capital, treasury, RCB, Constitution |
| **C** | 8–14 | Kernel release, trading path, broker safety |
| **D** | 15–18 | Control plane, human factors, infra |
| **E** | 19–22 | Strategy, cognitive, adequacy software, scenario harness |
| **F** | 23 | SIM calendar evidence (operational) |
| **G** | 24–25 | Compliance, security, LIVE DoD |
| **H** | 26–27 | LIVE-L1 entry, ramp, steady state |

### §18.1 P0 build sequence mapping

| §18.1 step | Primary phase(s) |
|------------|------------------|
| 1 Freeze sources, traceability | **1** |
| 2 Account identity, isolated domain | **2** |
| 3 Fact log | **3** |
| 4 Capital + treasury/reimbursement ledgers | **4**, **5** |
| 5 RCB + Constitution validation | **6**, **7** |
| 6 Crypto, signed artifacts, deploy pipeline | **8** |
| 7 Kernel + MT5 + credential custody | **9**, **10**, **11** |
| 8 OMS + reconciliation | **12**, **13** |
| 9 Halt/kill + global halt | **14**, **15** |
| 10 Web + Telegram + scope | **16**, **17** |
| 11 Monitoring, backup, restore | **18** |
| 12 Broker/compliance verification | **24** |
| 13 Resolve SIM/LIVE blockers | **24**, **25** |
| 14 Full P0 suite + drills | **22**, **25** |

---

## Phase 1 — Program foundation, governance, and engineering platform

**Maps to:** §18.1 step 1; §1.4–1.5; §16.1 (test taxonomy); §17 (risk register seed).

### Prerequisites

None (program start).

### Build scope

- Monorepo layout: kernel (Rust), control-api, web SPA, notifier-bot, MT5 bridge, shared schemas, infra-as-code for **A-only** topology ([independent-deployment-strategy.md](./independent-deployment-strategy.md)).
- **CI/CD:** build, lint, unit test, SAST dependency scan, artifact versioning, immutable release tags.
- **Requirements tooling:** [requirements-index.md](./requirements-index.md), [traceability-matrix.md](./traceability-matrix.md), [COVERAGE-CHECKLIST.md](./COVERAGE-CHECKLIST.md) wired to work tracking.
- **Decision log** with **A-DEC-01–10**, **OI-TG-01–06** (**OPEN** until owner acts).
- **Environment tiers:** dev, staging (SIM), pre-LIVE (staging with production-like controls), production (LIVE-capable but gated).
- **Secret management design:** no trade credentials outside kernel path; separate control tokens for Telegram.
- **Threat model v1:** kernel credential theft, Telegram reduce-only bypass, cross-group scope confusion, fact-log tampering.

### Requirements (representative)

Program traceability for all **A-*** families; no product **A-*** behaviour yet except governance hooks.

### Backlog

Enables all **A-P0-***; no §18 backlog item closed without downstream phase.

### Verification

- Design review checklist **§17.1** items 6–7 (assumption register; B-absent documented).
- CI green on empty/stub packages with contract tests for repo invariants.

### Exit criteria

- Every §1–20 section and Telegram §0–18 referenced in coverage checklist.
- **A-DEC-***/**OI-TG-*** visible; zero silent defaults documented.
- ADR: Group A independent deployment ratified.

### Design references

[01-system-overview-independence.md](./01-system-overview-independence.md), [COVERAGE-CHECKLIST.md](./COVERAGE-CHECKLIST.md), [decision-log.md](./decision-log.md).

---

## Phase 2 — Account identity registry and isolated Group A domain

**Maps to:** §18.1 step 2; §4.2 fingerprints; **A-IND-01–04** (data plane).

### Prerequisites

Phase **1**.

### Build scope

- **Account identity registry** service/schema: **A-SIM**, **A-LIVE** profiles; broker, server, login fingerprint fields; immutable history on change (**A-P0-01**).
- **Isolated A state store:** separate DB/schema/credentials; APIs reject Group B identifiers (**A-P0-03**).
- **Data contracts:** `account_mode` on all capital and risk projections (**A-MOD-03** foundation).
- Projection read models from fact log (stub consumers OK if Phase 3 not complete—contracts frozen).

### Requirements

**A-IND-01–03**, **A-MOD-02** (schema fields), **INV-02**, **INV-03** (store boundary).

### Backlog

**A-P0-01**, **A-P0-03** (partial until fact log Phase 3).

### Verification

| Class | Focus |
|-------|--------|
| **ISO** | Cross-group capital/risk mutation rejected |
| **UT** | Fingerprint validation, registry immutability rules |

### Exit criteria

- Registry and store deployed to staging; integration tests prove **no shared mutable cross-group risk state**.
- All services default scope **Group A** in configuration.

### Design references

[01-system-overview-independence.md](./01-system-overview-independence.md), [15-persistent-schemas-constitution.md](./15-persistent-schemas-constitution.md).

---

## Phase 3 — Fact log, event taxonomy, and audit chain

**Maps to:** §18.1 step 3; §12; **A-LOG-01–06**.

### Prerequisites

Phase **2**.

### Build scope

- Append-only **fact log** with hash chain (**A-LOG-05**), monotonic sequencing, writer identity.
- All **§12.1** event classes persist with IDs, timestamps, correlation IDs (**A-P0-02**).
- Write-failure policy: trading path behaviour on log unavailability (**A-LOG-06**).
- Read APIs: time-range query, category filter, export for audit (authenticated, scoped).
- Tamper-evidence verification tool (replay chain, detect break).

### Requirements

**A-LOG-01–06**, **A-PR-08** (journal events foundation), **INV-09**, **INV-10**.

### Backlog

**A-P0-02** complete.

### Verification

| Class | Focus |
|-------|--------|
| **UT** | Hash chain, schema validation |
| **IT** | Write → read projection; break detection |
| **SEC** | Unauthorized append rejected |

### Scenarios

Foundation for all **§15** scenarios (event emission contracts).

### Exit criteria

- Fact log is **the** system of record for control and capital events; staging soak ≥ 7 days without chain break.
- Downstream services consume via defined subscriptions or poll—no ad hoc DB writes bypassing log.

### Design references

[10-data-audit-fact-log.md](./10-data-audit-fact-log.md).

---

## Phase 4 — Five-state capital ledger and fee accounting

**Maps to:** §18.1 step 4 (capital); §3; **A-RCB-***, **A-FEE-***.

### Prerequisites

Phase **3**.

### Build scope

- **Capital ledger** with distinct types: equity, realised PnL, settled, reserved, withdrawable (**A-P0-04**, **INV-04**).
- **Fee engine hooks:** commission, swap accrual placeholders, FX at fill (**A-FEE-01–05** where ledger applies).
- **RCB input bindings:** equity vs RCB min() for limit calculations (service interface; full RCB Phase 6).
- Event-sourced updates from broker adapter (mock) and manual adjustment APIs (admin, scoped, logged).

### Requirements

**A-FEE-01–05**, **A-RCB-01–02** (read side), **INV-04**.

### Backlog

**A-P0-04** complete.

### Verification

| Class | Focus |
|-------|--------|
| **UT** | Type separation, withdrawal immediate RCB effect (**A-RCB-03** logic) |
| **TRE** | Ledger tie-out stubs |

### Scenarios

**CT-01**, **CT-02** (capital events) when wired to mock broker.

### Exit criteria

- Capital state reproducible from fact log + broker snapshots.
- No single field overloads “cash” semantics.

### Design references

[02-capital-rcb-treasury.md](./02-capital-rcb-treasury.md).

---

## Phase 5 — Reimbursement-owed ledger and treasury foundations

**Maps to:** §10.1, §10.3; **A-TRE-01–02**, **INV-05**.

### Prerequisites

Phase **4**.

### Build scope

- **Reimbursement-owed ledger** separate from broker cash (**A-P0-05**).
- Cost tagging model (**A-TRE-01**), owner-paid vs broker-deducted paths.
- Reimbursement state machine (**§10.3**) implemented with transitions logged.
- Treasury read API for web (read-only this phase).

### Requirements

**A-TRE-01–02**, **INV-05**; **A-OBL-01** schema (obligations tracking start).

### Backlog

**A-P0-05** complete.

### Verification

| Class | Focus |
|-------|--------|
| **TRE** | Reimbursement transitions |
| **UT** | Owner-paid costs never mixed with withdrawable without event |

### Exit criteria

- Treasury events appear in fact log; dashboards can show reimbursement status (web Phase 16 may consume).

### Design references

[02-capital-rcb-treasury.md](./02-capital-rcb-treasury.md).

---

## Phase 6 — RCB service, ratification, and cool-off rules

**Maps to:** §18.1 step 5 (RCB); §3.4; **A-RCB-03–08**.

### Prerequisites

Phase **4**, **5**.

### Build scope

- **RCB service:** deposits, withdrawals, ratification workflow (**A-P0-06**).
- **14-day cool-off** on RCB increase (**A-RCB-05**); deposit during halt inert (**A-RCB-06**).
- Web-exposed ratification (passkey stub OK until Phase 16—API must exist).
- Limits computed on **min(RCB, equity)** (**A-RCB-01–02**).

### Requirements

**A-RCB-01–08**.

### Backlog

**A-P0-06** complete.

### Verification

| Class | Focus |
|-------|--------|
| **UT** | Ratification timer, cool-off, halt inert deposit |
| **IT** | RCB change → kernel limit projection |

### Scenarios

**CT-03**, **CT-04**, **CT-A1**.

### Exit criteria

- RCB changes cannot bypass fact log; kernel consumes RCB version in verdict inputs.

### Design references

[02-capital-rcb-treasury.md](./02-capital-rcb-treasury.md), [03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md).

---

## Phase 7 — Constitution schema, signing, verification, activation

**Maps to:** §18.1 step 5; §8; **A-CON-01–04**; Appendix A.

### Prerequisites

Phase **1** (crypto design), **6**.

### Build scope

- **Constitution** JSON schema, example Appendix A loaded in staging (**A-P0-07**).
- Sign, verify, version pin, expiry rejection (**A-CON-01**).
- Time-lock for tighten/loosen (**A-CON-02–03**); pending changes visible.
- Kernel refuses unsigned/invalid Constitution (**A-CON-04** trade path).
- Emergency tighten-only path (no per-trade approval workflow).

### Requirements

**A-CON-01–04**.

### Backlog

**A-P0-07** complete.

### Blockers

**A-DEC-04** (time-lock hours)—implement as configurable fields; LIVE blocked until owner sets non-placeholder values.

### Verification

| Class | Focus |
|-------|--------|
| **SEC** | Signature failure, expired artifact |
| **DEP** | Constitution mismatch prevents kernel start |

### Exit criteria

- Only one active Constitution version per environment; activation events in fact log.

### Design references

[07-constitution-crypto-deployment.md](./07-constitution-crypto-deployment.md), [15-persistent-schemas-constitution.md](./15-persistent-schemas-constitution.md).

---

## Phase 8 — Cryptographic authority, kernel release engineering, and deploy pipeline

**Maps to:** §18.1 step 6; §8.3; **A-P0-19**.

### Prerequisites

Phase **7**.

### Build scope

- Code signing for **KERNEL-A** artifacts; provenance metadata (git SHA, constitution hash).
- **Deploy pipeline:** staged rollout, rollback, health gate, no manual binary swap in prod.
- **Frozen red-team suite** baseline (wrong signature, downgraded Constitution, tampered binary).
- Key ceremony documentation: generation, rotation, revocation (execute rotation drill in staging).

### Requirements

Supports **A-KRN-02**, **A-PR-02**, **A-CON-01**.

### Backlog

**A-P0-19** complete.

### Verification

| Class | Focus |
|-------|--------|
| **DEP** | Only signed kernel deploys |
| **RT** | Red-team cases from §16.2 subset |

### Exit criteria

- Production path cannot run unsigned kernel; rollback tested ≤ 15 minutes in staging.

### Design references

[07-constitution-crypto-deployment.md](./07-constitution-crypto-deployment.md).

---

## Phase 9 — KERNEL-A runtime, verdict engine, and intent path

**Maps to:** §18.1 step 7; §6; **A-P0-09**, **A-KRN-01–08**.

### Prerequisites

Phases **3**, **6**, **7**, **8**.

### Build scope

- **KERNEL-A** process: load Constitution, RCB, mode, halt state; **intent → verdict** pipeline (**§6.1**, **§6.4** check order).
- Verdict persistence; no broker submit without **APPROVE** (**INV-01**).
- Halt state in kernel memory + durable store (**A-KRN-05**).
- Latency instrumentation (**A-KRN-07**); structured reject reason codes.
- Poll cadence hooks for broker (**A-KRN-03** interface).

### Requirements

**A-KRN-01–08**, **A-PR-02**.

### Backlog

**A-P0-09** complete (adapter Phase 11 may stub broker).

### Verification

| Class | Focus |
|-------|--------|
| **UT** | Verdict ordering, halt blocks |
| **RT** | Oversized intent, wrong mode |
| **PERF** | Verdict latency baseline |

### Scenarios

**TS-05**, **TS-06**, **TS-09** (kernel-side rejects).

### Exit criteria

- Kernel runs 24h staging with mock adapter; 100% intents receive verdict; fact log complete.

### Design references

[05-kernel-oms-reconciliation.md](./05-kernel-oms-reconciliation.md).

---

## Phase 10 — Kernel-only credential vault and custody boundaries

**Maps to:** §18.1 step 7; **A-P0-08**; **A-PR-02**.

### Prerequisites

Phase **9**.

### Build scope

- **Credential vault** inside kernel boundary; encrypted at rest; memory zeroization policy.
- MT5 credentials inject only at kernel startup; rotation procedure.
- Negative tests: control-api, notifier-bot, web **cannot** read trade credentials.
- Audit log on credential use (not secret values).

### Requirements

**A-KRN-02**, **A-PR-02**, **A-MOD-05** (no live creds on SIM host path—enforced in config Phase **19**).

### Backlog

**A-P0-08** complete.

### Verification

| Class | Focus |
|-------|--------|
| **SEC** | Credential isolation |
| **ISO** | Non-kernel processes denied |

### Exit criteria

- Penetration-style test report: no credential exfiltration via control plane APIs.

### Design references

[05-kernel-oms-reconciliation.md](./05-kernel-oms-reconciliation.md), [06-broker-exness-mt5.md](./06-broker-exness-mt5.md).

---

## Phase 11 — Exness MT5 adapter, ZeroMQ bridge, and market session integration

**Maps to:** §18.1 step 7; §7; **A-P0-10**.

### Prerequisites

Phases **9**, **10**; Windows host provisioning started (**Phase 19** parallel allowed).

### Build scope

- **MT5 adapter** normalizing §7.1 contract; thread-pooled sync calls; ZeroMQ bridge to Windows terminal.
- Account fingerprint verification on connect (**A-MOD-02**).
- Demo account SIM path end-to-end: connect, subscribe, order placeholder (full orders Phase 12–14).
- Contract spec cache: min lot, step, stops level (**feeds A-DEC-01** analysis).

### Requirements

§7.1–7.3 adapter behaviours; **A-MOD-02**.

### Backlog

**A-P0-10** complete.

### Appendix D

MT5 Python terms (**Phase 11** verify); latency baseline begins.

### Verification

| Class | Focus |
|-------|--------|
| **BAT** | Adapter contract tests |
| **FI** | Bridge disconnect **BF-A1** |

### Exit criteria

- Demo account stable ≥ 5 sessions; reconnect without duplicate ghost orders (with OMS Phase 12).

### Design references

[06-broker-exness-mt5.md](./06-broker-exness-mt5.md), [independent-deployment-strategy.md](./independent-deployment-strategy.md).

---

## Phase 12 — Order management system and idempotency

**Maps to:** §18.1 step 8; **A-P0-11**, **A-OMS-01–05**.

### Prerequisites

Phases **9**, **11**.

### Build scope

- **OMS:** client correlation IDs, state machine (new → submitted → partial → filled → cancelled → failed).
- Idempotency keys; retry rules (**A-OMS-01–05**); no duplicate live orders on timeout/retry.
- Integration kernel verdict → OMS → adapter submit.
- Dead-letter and manual reconciliation queue UI hooks.

### Requirements

**A-OMS-01–05**.

### Backlog

**A-P0-11** complete.

### Verification

| Class | Focus |
|-------|--------|
| **UT** | Idempotency table |
| **IT** | Retry does not duplicate |

### Scenarios

**TS-07**, **TS-08**, **TS-11** (partial fill, duplicate intent).

### Exit criteria

- Chaos tests: forced timeout → at most one broker order per intent.

### Design references

[05-kernel-oms-reconciliation.md](./05-kernel-oms-reconciliation.md).

---

## Phase 13 — Reconciliation engine and trading recovery

**Maps to:** §18.1 step 8; **A-P0-12**, **A-REC-01–04**.

### Prerequisites

Phase **12**.

### Build scope

- **Reconciliation:** event-driven + **5s poll** (**A-KRN-03**, **A-REC-***).
- Mismatch detection before retry/resume (**A-REC-02**).
- Positions, orders, balances vs broker truth (**A-PR-03**).
- Automatic **L2** escalation paths per §9.1 (coordination with Phase 14).

### Requirements

**A-REC-01–04**, **A-PR-03**.

### Backlog

**A-P0-12** complete.

### Verification

| Class | Focus |
|-------|--------|
| **REC** | Mismatch injection |
| **OPS** | Runbook **C.3** executable |

### Scenarios

**HL-B**, **BF-02**, **BF-03**.

### Exit criteria

- Injected mismatch halts new risk within SLA defined in Constitution (default: immediate block).

### Design references

[05-kernel-oms-reconciliation.md](./05-kernel-oms-reconciliation.md), [13-scenarios-runbooks.md](./13-scenarios-runbooks.md).

---

## Phase 14 — Execution guards, protective stops, and cost gates

**Maps to:** §5.4, §6; **A-P0-13**, **A-EXE-01–04**, **A-SZ-01–04** (kernel enforcement).

### Prerequisites

Phases **12**, **13**.

### Build scope

- **Protective stop** mandatory on entry (**A-EXE-03**, **A-P0-13**); reject `untradeable_at_this_capital` (**TS-04**).
- News blackout, swap guard, slippage budget L1 (**A-EXE-01–02**, **A-EXE-04**).
- Lot step down-round, min lot interaction (**A-SZ-02**)—behaviour for **A-DEC-01** / **A-P0-21** implemented both paths behind flag.
- Stale tick block (**TS-10**).

### Requirements

**A-EXE-01–04**, **A-SZ-01–04** (enforcement layer).

### Backlog

**A-P0-13** complete; **A-P0-21** implementation with **BLOCKED** flag until **A-DEC-01**.

### Verification

| Class | Focus |
|-------|--------|
| **BAT** | Stop attachment verification |
| **PERF** | Slippage measurement |

### Scenarios

**TS-01–04**, **TS-10**, **TS-12**, **TS-13**.

### Exit criteria

- Zero entries without verified broker-side stop in demo; stop failure → reject + fact log.

### Design references

[04-strategy-quant-engine.md](./04-strategy-quant-engine.md), [05-kernel-oms-reconciliation.md](./05-kernel-oms-reconciliation.md).

---

## Phase 15 — Halt ladder, kill switch, mode state machine, global halt

**Maps to:** §18.1 step 9; §9; **A-P0-14**, **A-P0-15**, **A-KIL-01–06**.

### Prerequisites

Phases **9**, **13**.

### Build scope

- **Halt ladder L1–L4** (**§9.1**); owner kill **K1–K3** (**§9.2**).
- **Mode state machine:** SIM, LIVE-L1, MANAGE_ONLY, HALTED (**A-P0-15**).
- **Global halt** protocol; B-absent partial confirmation (**§9.3**, **INV-06**, **A-IND-04**).
- Kill drills scheduling (**A-KIL-06**).

### Requirements

**A-KIL-01–06**, **A-MOD-04** (badges feed Phase 16–17).

### Backlog

**A-P0-14**, **A-P0-15** complete.

### Verification

| Class | Focus |
|-------|--------|
| **HALT** | **HL-01–02**, **HL-07–08**, **HL-A–F** |
| **OPS** | Runbook **C.1** |

### Scenarios

**OC-01–06**, **OC-04** (ALL partial).

### Exit criteria

- Three kill levels exercised in SIM at phase gate; mode transitions auditable in fact log.

### Design references

[08-halts-kill-checkin.md](./08-halts-kill-checkin.md).

---

## Phase 16 — Owner check-in, away mode, and email notification path

**Maps to:** §9.4; **A-CHK-01–05**; Appendix D email provider.

### Prerequisites

Phase **15**; fact log Phase **3**.

### Build scope

- **Check-in timer in kernel** (**A-CHK-03**); lapsed behaviour **OP-05**, **C.6**.
- Web passkey check-in + away mode (**A-CHK-01–02**); Telegram `/alive` reduce-only.
- **Email** reminders (provider chosen and tested—Appendix D).
- Trusted contact notifications (informational only, **A-CHK-04**).

### Requirements

**A-CHK-01–05**.

### Backlog

Cross-cutting; enables **OPS** drills.

### Verification

| Class | Focus |
|-------|--------|
| **HALT** | Check-in lapse paths |
| **OPS** | **OP-01–06** |

### Exit criteria

- Timer runs with kernel offline web; day 10/day 14 effects tested in SIM (**A-CHK-05**).

### Design references

[08-halts-kill-checkin.md](./08-halts-kill-checkin.md), [11-web-control-api.md](./11-web-control-api.md).

---

## Phase 17 — Web control-api, SPA, scope enforcement, LIVE arming UX

**Maps to:** §18.1 step 10 (web); §13.2–13.3; **A-P0-16**, **A-TG-** (web parity).

### Prerequisites

Phases **6**, **7**, **15**, **16**.

### Build scope

- **control-api:** authenticated, **group-scoped** authorisation (**A-P0-16**, **A-IND-02**).
- SPA pages: capital, RCB ratification, mode badges, halt status, Constitution read-only, check-in/away, SIM/LIVE arming wizard (**§4.3** UI steps—not final LIVE until Phase 26–27).
- Passkey for risk-increasing actions (**A-PR-05**).
- Reporting labels: combined figures **reporting-only** (**INV-03**).

### Requirements

§13.2–13.3, **A-IND-02**, **A-MOD-04**, **A-TG-01–03** (web side).

### Verification

| Class | Focus |
|-------|--------|
| **ISO** | Cross-group API denial |
| **SEC** | Passkey required paths |
| **OPS** | **AM-02**, **AM-03** (preflight UI) |

### Exit criteria

- Full owner SIM operations without Telegram; all control actions in fact log.

### Design references

[11-web-control-api.md](./11-web-control-api.md).

---

## Phase 18 — Telegram notifier-bot (reduce-only control plane)

**Maps to:** §18.1 step 10 (Telegram); §13.4; Telegram spec §0–15; **TG-PO-01–10**, **TG-01–16**, **SEC-01–07**.

### Prerequisites

Phases **15**, **17** (control-api integration).

### Build scope

- **notifier-bot** process: keyboards, notifications, signed expiring confirm buttons, scope tags (**A-TG-04–06**).
- **Reduce-only:** no resume, SIM→LIVE, limit loosen (**TG-T-07**).
- Allowlist, replay dedup, fact log for every message (**TG-01–05**).
- Rate limit / batching hooks (**TG-13**, **OI-TG-05** configurable—not silent defaults).
- **TG-PO-01–10** delivered.

### Requirements

Full Telegram **TG-***, **SEC-***, **A-TG-01–06** (stricter union).

### Verification

| Class | Focus |
|-------|--------|
| **TG** | **TG-T-01–15** |
| **SEC** | Token scope, **TG-S-15** |

### Scenarios

**TG-S-01–25** (mapped subset for P0 flows).

### Exit criteria

- Negative auth suite passes: bot cannot arm LIVE or loosen limits; CRITICAL never suppressed.

### Design references

[telegram-interface.md](./telegram-interface.md).

---

## Phase 19 — Observability, critical alerting, backup, DR, and Windows host

**Maps to:** §18.1 step 11; §14; **A-P0-17**, **A-P0-18**; **A-DEC-07**, **A-DEC-09**.

### Prerequisites

Phases **3**, **9**, **11**.

### Build scope

- Metrics, logs, traces; SLO dashboards; on-call routing.
- **CRITICAL** alert path non-suppressible (**§14.1**, **A-P0-17**).
- Encrypted backups, **monthly restore drill**, hash-chain verify on restore (**A-P0-18**, **C.2**).
- **Windows host** provisioned (**A-DEC-07** recorded); network policy per [independent-deployment-strategy.md](./independent-deployment-strategy.md).
- Market-data/news licence compliance hooks (Appendix D).

### Requirements

§14, **A-LOG-04** (monitoring integration).

### Backlog

**A-P0-17**, **A-P0-18** complete.

### Blockers

**A-DEC-09**: RPO/RTO numeric targets required for LIVE exit Phase **25**—implement tooling now, values owner-set.

### Verification

| Class | Focus |
|-------|--------|
| **DR** | Restore + chain integrity |
| **OPS** | Heartbeat loss **C.2** |

### Exit criteria

- Successful restore from backup to clean host; MT5 bridge monitored; alert fire ≤ 60s on injected kernel stall.

### Design references

[12-monitoring-backup-continuity.md](./12-monitoring-backup-continuity.md).

---

## Phase 20 — Strategy engine, universe, sizing, and SIM trading loop

**Maps to:** §5; §6.2 Intent; **A-UNI-***, **A-SIG-***, **A-SZ-***, **A-MOD-01**.

### Prerequisites

Phases **14**, **11** (demo trading).

### Build scope

- Mode-agnostic strategy producing **Intent** schema (**§6.2**).
- Kalman (**A-SIG-01**), regime filter (**A-SIG-02**—**N** via Constitution or **BLOCKED**), BL (**A-SIG-03–04**).
- Risk-budget sizing (**A-SZ-01–04**); LIVE-L1 universe EUR/USD (**A-UNI-01**).
- Continuous SIM loop; decision journal before action (**§12.3**, **A-PR-08**).
- Vectorised backtest with full cost model (**§5.5**); no LLM in execution path.

### Requirements

**A-UNI-01–03**, **A-SIG-01–04**, **A-SZ-01–04**, **A-MOD-01**, **A-PR-04**, **A-PR-06**.

### Verification

| Class | Focus |
|-------|--------|
| **UT** | Sizing, regime abstain |
| **MOD** | Intent schema |
| **IT** | SIM week run |

### Scenarios

**TS-01–03**, **TS-09**, **MP-01–03** (infra only).

### Exit criteria

- ≥ 4 weeks automated SIM sessions with intents, verdicts, orders, stops on demo; journal completeness 100%.

### Design references

[04-strategy-quant-engine.md](./04-strategy-quant-engine.md).

---

## Phase 21 — Cognitive plane integration (SIM shadow)

**Maps to:** §11; **A-COG-01–03**; **CG-LIVE** prep only.

### Prerequisites

Phase **20**.

### Build scope

- **AdvisorySignal** ingestion; invalid → zero view (**A-COG-01**).
- Calibration table (**A-COG-02**); injection-safe handling (**A-COG-03**).
- Shadow evaluation metrics export for **CG-LIVE** (**A-COG-04**—methodology documented, threshold **not invented**).
- No advisory-driven orders without explicit future gate approval.

### Requirements

**A-COG-01–03**; **A-COG-04** shadow only.

### Verification

| Class | Focus |
|-------|--------|
| **SEC** | Prompt injection cannot create order path |
| **MOD** | Abstain paths **TS-02–03** |

### Exit criteria

- LIVE-capable code path exists with advisory multiplier **0**; shadow report generated weekly in SIM.

### Design references

[09-cognitive-plane.md](./09-cognitive-plane.md).

---

## Phase 22 — SIM-adequacy engine, cost allocation, dashboards, scenario harness

**Maps to:** §4.5; §15; §18 P1; **A-P1-01**, **A-P1-04**, **A-P1-05**, **A-P1-07**.

### Prerequisites

Phases **20**, **21**, **18** (ops visibility).

### Build scope

- **SIM-adequacy engine** computing **A-SIM-01–08** criteria with stored evidence (**A-P1-01**).
- **Cost allocation** events (**A-P1-04**, **A-DEC-05** configurable).
- Champion/challenger runner (**A-P1-05**); frozen promotion gate params.
- Performance dashboards net-of-cost (**A-PERF-01–02**, **A-P1-07**).
- Automated **§15** scenario runner (TS, HL, OC, AM, CT, BF, MP families) tied to CI nightly.

### Requirements

**A-SIM-01–08** (software); **A-P1-01–05**, **A-P1-07**.

### Blockers

**A-DEC-03** blocks final “pass” output until hurdle defined.

### Verification

| Class | Focus |
|-------|--------|
| **MOD** | Adequacy reproducibility |
| **OPS** | Scenario catalog |
| **TRE** | Cost allocation |

### Exit criteria

- One-click adequacy report from stored facts; scenario suite green in staging.

### Design references

[03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md), [13-scenarios-runbooks.md](./13-scenarios-runbooks.md), [14-verification-risks-live-gates.md](./14-verification-risks-live-gates.md).

---

## Phase 23 — SIM operations evidence period (calendar gate)

**Maps to:** **A-SIM-01** (≥ 6 months); §4.5; operational not sprint.

### Prerequisites

Phase **22**; stable SIM loop Phase **20**.

### Build scope

- Operate SIM at reference floor sizing continuously (**A-SIM-08**).
- Collect reconciliation clean rate (**A-SIM-02**), halt history (**A-SIM-06**), bootstrap/trade count (**A-SIM-05**).
- Execute scheduled drills: **C.3**, **C.6**, **C.9**, **C.10**, reverse graduation **AM-A5**.
- Kalman params frozen last 3 months (**A-SIM-07**).

### Requirements

Evidence for **A-SIM-***; no new feature development except defect fixes and evidence gaps.

### Verification

| Class | Focus |
|-------|--------|
| **MOD** | §4.5 gate inputs |
| **REC** | 95% trajectory **A-SIM-02** |
| **OPS** | Drill log |

### Exit criteria

- Calendar ≥ 6 months; adequacy report shows pass/fail per criterion; no **L2+** in last 60 days (**A-SIM-06**).

### Note

Software from Phase **22** must remain unchanged except versioned bugfixes—parameter changes restart relevant clocks per §4.5.

### Design references

[03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md).

---

## Phase 24 — Broker, account, tax verification and blocker resolution

**Maps to:** §18.1 steps 12–13; §7.4; **A-P0-20**; **A-DEC-01**, **A-DEC-08**, **A-DEC-10**.

### Prerequisites

Phases **11**, **14**, **19**.

### Build scope

- **Evidence package** store: Kenya Exness account type, leverage, products, withdrawals, protective orders (**§7.4**).
- Tax/reporting memo slot (**A-FEE-05**, Appendix D).
- Formal resolution or **BLOCKED** acceptance for **A-DEC-01** (min lot vs cap), **A-DEC-08** (emergency relay), **A-DEC-10**.
- Written sign-off artifact linked in preflight engine.

### Requirements

**A-P0-20** complete; **INV-08** evidence.

### Verification

| Class | Focus |
|-------|--------|
| **BAT** | Protective order live verification |
| **SEC** | Relay policy if enabled |

### Exit criteria

- Unknown broker rules remain **disabled** in preflight; owner sign-off recorded or LIVE remains impossible.

### Design references

[06-broker-exness-mt5.md](./06-broker-exness-mt5.md), [decision-log.md](./decision-log.md).

---

## Phase 25 — Security hardening, full verification suite, and §19 LIVE readiness

**Maps to:** §16–19; §18.1 step 14; **A-P1-06**; **CG-LIVE** decision record.

### Prerequisites

Phases **18**, **22**, **23**, **24**.

### Build scope

- Execute full **§16.1** test matrix at required gates; all **INV-01–INV-11**.
- **LIVE preflight engine** with explicit reason codes (**A-P1-06**, **AM-03**).
- **§17.1** design review at LIVE gate.
- **CG-LIVE:** document advisory gate pass/fail criteria (**A-COG-04**) or confirm advisory=0 for initial LIVE.
- Resolve **A-DEC-04**, **A-DEC-09** for LIVE (or LIVE stays blocked).

### Requirements

§19 “Complete when” rows: Architecture, Code, Security, Testing, Broker, Operations.

### Backlog

**A-P1-06** complete; **TG-PO-11–15** (P1 Telegram) if not done in Phase 18.

### Verification

All classes: **UT, IT, BAT, REC, STM, INV, ISO, SEC, RT, FI, DR, DEP, TRE, HALT, PERF, MOD, OPS, TG**.

### Exit criteria

- Preflight returns pass only when §19 table satisfied; owner can complete arming checklist except final LIVE switch (Phase 26–27).

### Design references

[14-verification-risks-live-gates.md](./14-verification-risks-live-gates.md).

---

## Phase 26 — LIVE-L1 arming, SIM→LIVE procedure, and first production session

**Maps to:** §4.3–4.4; **AM-01**, **AM-A1**; Appendix C **C.4**.

### Prerequisites

Phase **25** preflight pass; capital **RCB ≥ reference floor** (necessary, not sufficient).

### Build scope

- Execute **§4.3**: 24h arming → Telegram code (**OI-TG-01**) → web confirm → safe window.
- First LIVE-L1 orders with **0.25× ramp** start; ramp clock (**§4.5**).
- **Shadow twin** start (**A-P1-03**, **A-SWT-03**).
- Post-session reconciliation and fact log audit mandatory.

### Requirements

**A-SWT-01–04** (L1 paths); **A-LAD-04–06** (ramp rules).

### Backlog

**A-P1-02** (L1 subset), **A-P1-03**.

### Verification

| Class | Focus |
|-------|--------|
| **STM** | Mode transitions **AM-01–07** |
| **OPS** | **C.4** runbook |

### Exit criteria

- First LIVE session completed with stops verified on broker; no manual bypass of preflight.

### Design references

[03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md), [13-scenarios-runbooks.md](./13-scenarios-runbooks.md).

---

## Phase 27 — Ramp completion, steady LIVE-L1, treasury payouts, and L2/L3 stubs

**Maps to:** §4.5 ladder; **A-P1-02**; **A-DEC-02**; §10.5; **A-P2-01** optional.

### Prerequisites

Phase **26**; **30-day minimum ramp** (**§4.5**); 90-day evidence clock independent.

### Build scope

- **Reverse graduation** live (**A-LAD-01–03**); floor rules (**A-LAD-05–06**).
- **LIVE-L2/L3** code paths implemented but **feature-flag disabled** until **A-DEC-02**.
- Steady monitoring, treasury reimbursement schedule (**§10.5**), manual withdrawal runbook **C.8**.
- Divergence reports SIM vs LIVE (**A-P1-03**).
- **A-P2-01** research modules off by default behind gates.

### Requirements

**A-LAD-01–06**, **A-OBL-02–03**, **A-TRE-03–06**.

### Verification

| Class | Focus |
|-------|--------|
| **HALT** | **HL-02** recovery in LIVE or staged account |
| **OPS** | Kill **K2** drill, **CT-05**, **BF-01–BF-A3** |

### Exit criteria

- LIVE-L1 steady state documented; incident playbooks proven; program “implementation complete” per §19 with LIVE-L1 operating under Constitution.

### Design references

[02-capital-rcb-treasury.md](./02-capital-rcb-treasury.md), [03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md).

---

## Cross-phase backlog matrix (§18)

| Backlog ID | Phase(s) | Notes |
|------------|----------|-------|
| A-P0-01 | 2 | |
| A-P0-02 | 3 | |
| A-P0-03 | 2 | |
| A-P0-04 | 4 | |
| A-P0-05 | 5 | |
| A-P0-06 | 6 | |
| A-P0-07 | 7 | |
| A-P0-08 | 10 | |
| A-P0-09 | 9 | |
| A-P0-10 | 11 | |
| A-P0-11 | 12 | |
| A-P0-12 | 13 | |
| A-P0-13 | 14 | |
| A-P0-14 | 15 | |
| A-P0-15 | 15 | |
| A-P0-16 | 17, 18 | Web + Telegram paths |
| A-P0-17 | 19 | |
| A-P0-18 | 19 | |
| A-P0-19 | 8 | |
| A-P0-20 | 24 | |
| A-P0-21 | 14, 24 | **A-DEC-01** |
| A-P1-01 | 22, 23 | |
| A-P1-02 | 26, 27 | L2/L3 blocked **A-DEC-02** |
| A-P1-03 | 26, 27 | |
| A-P1-04 | 22 | **A-DEC-05** |
| A-P1-05 | 22 | |
| A-P1-06 | 25, 26 | |
| A-P1-07 | 22 | |
| A-P2-01 | 27+ | Post-L1 |
| TG-PO-01–10 | 18 | |
| TG-PO-11–15 | 18, 25 | P1 features |

---

## Cognitive gate **CG-LIVE** (§11, **A-COG-04**)

| Step | Implementation phase | Action |
|------|---------------------|--------|
| Shadow metrics | **21** | Rank correlation, calibration, P&L contribution vs zero |
| Owner criteria | **25** | Document pass/fail; no engineering-invented threshold |
| LIVE economics | **26–27** | If not passed, **A-COG-01** zero view—valid production state |

---

## Definition of Done (§19) vs phases

| §19 area | Primary completion phase |
|----------|-------------------------|
| Architecture | **25** (boundaries enforced) |
| Code | **25** (P0/P1 or BLOCKED) |
| Security | **25** |
| Testing | **25** (+ **23** SIM evidence) |
| Broker | **24** |
| Operations | **25**, **27** (steady state) |

**LIVE eligibility** remains an **evidence predicate** evaluated by preflight—not a single phase flip.

---

## Document section index (quick reference)

| Topic | Group A § | Primary phases |
|-------|-----------|----------------|
| Independence | 1.3 | 2, 17 |
| Capital / RCB | 3 | 4–6 |
| Modes / SIM / ladder | 4 | 15, 22–23, 26–27 |
| Strategy | 5 | 20 |
| Kernel / OMS / recon | 6 | 9–13 |
| Broker | 7 | 11, 24 |
| Constitution / deploy | 8 | 7–8 |
| Halts / check-in | 9 | 15–16 |
| Treasury | 10 | 5, 22, 27 |
| Cognitive | 11 | 21, 25 (**CG-LIVE**) |
| Fact log | 12 | 3 |
| Web / Telegram | 13 | 17–18 |
| Monitoring / backup | 14 | 19 |
| Scenarios | 15 | 22 |
| Verification | 16 | 25 |
| LIVE eligibility | 19 | 25–27 |

| Topic | Telegram spec § | Phase |
|-------|-----------------|-------|
| Full reduce-only UX | 0–15 | **18** |
| Tests / DoD | 14–16 | **18**, **25** |
