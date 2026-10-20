# Group A — Independent Deployment Strategy

**Purpose:** Define how Group A is built, hosted, and operated as a **complete, self-contained system** while Group B is not yet deployed (or is stopped), without violating the independence contract in Group A **§1.3** or the shared halt rules in **§9.3**.

**Authority:** Subordinate to [`docs/source/SATE_Group_A_System_Documentation.docx`](../../source/SATE_Group_A_System_Documentation.docx). Cross-check Group B **§1.3** only for symmetric isolation rules.

**Related design:** [01-system-overview-independence.md](./01-system-overview-independence.md) (§1.3–2.6), [architecture-components.md](./architecture-components.md) (components), [06-broker-exness-mt5.md](./06-broker-exness-mt5.md) (Windows/MT5), [08-halts-kill-checkin.md](./08-halts-kill-checkin.md) (partial ALL halt), [telegram-interface.md](./telegram-interface.md) (notifier-bot placement).

---

## 1. Design intent

Group A **§1.1–1.2** states that Group A has its own broker profile, capital, RCB, Constitution, kernel, mode machine, treasury, halt state, and performance record, and **does not depend on Group B** to trade, to be eligible for LIVE, or to size risk.

**A-IND-04:** Group A shall continue to operate with its own halt and protective controls if Group B is stopped, halted, or unreachable. The **only couplings** are:

1. **Reporting** (optional combined views, explicitly labelled reporting-only — Telegram **TG-14**, Group A **§13.3**).
2. **ALL-scope halt confirmation** (**§9.3**): `HALT_CONFIRMED_ALL` requires both kernels or approved broker emergency control — never inference from unreachability (**INV-06**).

This strategy satisfies A-IND-04 by deploying Group A end-to-end first, with shared services that are **scope-aware** and **fail closed** on ALL-scope when Group B is absent.

---

## 2. Deployment profiles

### 2.1 Profile A-only (initial)

Used from **implementation Phase 2** through **Phase 27** (LIVE-L1 steady state) until Group B is intentionally deployed.

| Concern | Choice | Source reference |
|---------|--------|------------------|
| Trading execution | **KERNEL-A** + MT5 bridge + dual terminals (demo/live) on **Windows** | §2.3, §7.3, A-DEC-07 |
| Strategy / signals | Python (or designated) process on Windows or co-located; **no broker credentials** | §6.1, A-PR-02, A-KRN-02 |
| Fact log, capital, RCB, treasury DB | Linux (or Windows) on private network; **`group_scope = A`** on all A records | §12, A-P0-02–06 |
| Web control plane | Private SPA + **control-api**; passkey for risk-increasing actions | §13.2–13.3 |
| Telegram | **notifier-bot**; reduce-only; scope **A** default | Telegram spec §0–1, Group A §13.4 |
| Cognitive plane | Optional; **advisory only**; failure ⇒ zero view | §11, A-COG-01 |
| Group B kernel | **Not deployed** | §1.3 |
| Halt service | Deployed with **B unreachable** semantics | §9.3, Telegram TG-15 |

### 2.2 Profile A + B (future)

When Group B is added, **no Group A deployment change** may introduce cross-group capital or combined sizing (**INV-02**, **ISO** tests §16.1). Add **KERNEL-B** and Alpaca adapter on their documented host (Group B doc §2.3); extend halt coordination to dual acknowledgement.

---

## 3. Physical and network topology

Group A **§2.3** and **§7.3** require a **Windows host** near Exness server region (latency for fill quality). Hosting is built in **implementation Phases 11 and 19** ([implementation-phases.md](./implementation-phases.md); **A-DEC-07**).

```
                    +------------------ Private overlay (WireGuard / Tailscale) ------------------+
                    |                                                                               |
  Owner devices     |   +------------------+         +------------------------+                    |
  (Web passkey,     |   |  control-api     |<------->|  dashboard-api (opt.)  |                    |
   Telegram) ------+-->|  + web SPA       |         +------------------------+                    |
                    |   +--------+---------+                    ^                                  |
                    |            | limited control token         | read APIs, scope A               |
                    |            v                               |                                  |
                    |   +------------------+    event stream     +------------------+               |
                    |   |  notifier-bot    |<-------------------|  fact log        |               |
                    |   |  (Telegram)      |                    |  + A state store |               |
                    |   +------------------+                    +--------+---------+               |
                    |            |                                         ^                         |
                    |            | halt/kill/mode (scope A)               |                         |
                    |            v                                         |                         |
                    |   +------------------+         IPC (local socket)  |                         |
                    |   |  halt coordinator|----------------------------->|                         |
                    |   +------------------+                              |                         |
                    +---------------------------|---------------------------|-------------------------+
                                                |                           |
                                     encrypted  |                           |  metrics/alerts
                                     tunnel     |                           |
                                                v                           v
                    +--------------------------- Windows host (Group A execution) ------------------+
                    |  KERNEL-A (Rust)  <-->  MT5 bridge (Python, thread pool)  <-->  MT5 terminals |
                    |       |                      ZeroMQ — not on strategy event loop   demo | live   |
                    |       +--> Exness (demo SIM / real LIVE)                                              |
                    +-------------------------------------------------------------------------------------+
```

### 3.1 Host responsibilities

| Host | Processes | Credentials | Source |
|------|-----------|-------------|--------|
| **Windows (A-exec)** | KERNEL-A, MT5 bridge, MT5 demo terminal, MT5 live terminal (separate portable installs), optional strategy runner | **Trade-capable keys only inside KERNEL-A** | A-KRN-02, A-MOD-05, §7.3 |
| **Private network (A-control)** | fact log service, PostgreSQL/SQLite (A-scoped), RCB, treasury, control-api, monitoring, backups, notifier-bot | Bot token + **limited control token** only on bot; no broker trade keys | Telegram §0 princ. 6, §13.1 |
| **Owner client** | Browser (WebAuthn), Telegram app | Passkey; allowlisted Telegram user | §13.3, A-TG-03 |

### 3.2 Segregation rules

1. **A-MOD-05:** Live credentials shall not be present on SIM-only paths where the broker allows separation — use **separate terminal instances** and profiles (**§7.3**).
2. **A-MOD-02:** Fingerprint (account number + server) verified at startup, reconnect, and poll intervals — mismatch ⇒ **HL-C** / immediate halt.
3. **NTP** on every host; broker server time on every event (**§7.1**, R-79).
4. Firewall: MT5 reachable only from bridge; KERNEL-A API only from control-api and local signed CLI (**§9.2**).

---

## 4. Shared services in an A-only deployment

Group A **§2.6** lists shared services Group A consumes. In A-only mode:

| Service | A-only behaviour | Must not |
|---------|------------------|----------|
| Fact log | All events tagged `group_scope = A` (or GLOBAL for infra) | Approve trades (**A-LOG-**, §2.6) |
| Market-data ingestion | Normalised A instruments + freshness | Trade authority |
| Halt service | Accept **scope A**; **scope ALL** ⇒ `HALT_REQUESTED` until B ack or timeout → **partial state only** | Assert `HALT_CONFIRMED_ALL` without B (**§9.3**, **INV-06**) |
| Web + Telegram | Enforce **scope A** server-side (**A-P0-16**) | Cross-group capital in APIs (**A-IND-02**) |
| Monitoring | A-scoped metrics; CRITICAL never flood-suppressed | §14.1 |
| Backup/restore | Encrypted; A state + fact log | Restore without verification (**§14.2**) |
| Crypto authority | Distinct keys per scope; pinned verify keys | §8.3, R-85 |
| Telegram bot | Reduce-only; [A-SIM]/[A-LIVE] tags | Exposure-increasing commands (**TG-09**) |
| Cognitive plane | Signed `AdvisorySignal`; TTL < horizon | Order/sizing/credential authority (**§11**) |

**Reporting stub for Group B:** Dashboard may show Group B panel as **“Not deployed”** — no combined totals unless labelled *Combined reporting — not transferable and not used for sizing or eligibility* (Group A §13.3, Telegram **TG-14**).

---

## 5. Data domain isolation

Implement **A-P0-03** (isolated A state store) as:

1. **Schema:** Every capital-bearing row includes `group_id = A`, `broker_id`, `account_id`, `environment` (SIM/LIVE) — **A-IND-01**.
2. **API:** Risk-bearing endpoints require explicit `scope=A`; reject GLOBAL or B-sourced capital — **A-IND-02**.
3. **Migrations:** No shared mutable “portfolio total” table used by kernel or sizing services — **INV-03**.
4. **Tests:** **ISO** and **INV** suite (§16.1–16.3), including injection of combined RCB and cross-group gate requests (§1.3 verification table).

---

## 6. Operational independence scenarios

Map to Group A **§15** (selected):

| Scenario ID | A-only expectation |
|-------------|-------------------|
| **AM-06** | Group B mode changes have **no effect** on A — trivially satisfied when B absent |
| **OC-04** | Kill ALL while B unreachable → **HALT_CONFIRMED_A** only; UI/Telegram show partial halt (**TG-15**, **TG-S-16**) |
| **BF-07** | Kernel failure → fail closed; **broker-side stops** protect (**A-KRN-01**, R-19) |
| **OP-05** | Check-in lapse in SIM → SIM continues (**§9.4**, **OP-05**) |
| **CT-07** | Cross-broker transfer flag — in A-only, only A broker; B liquidity N/A |

Runbooks **Appendix C** apply to Group A processes only; B-specific steps are out of scope until Profile A+B.

---

## 7. Rollout sequence (deployment actions)

Aligned with Group A **§18.1 P0 build sequence** and [implementation-phases.md](./implementation-phases.md) (**Phases 1–27**):

1. Provision **private overlay** and secrets vault (no credentials in git) — **Phase 1**.
2. Deploy identity store, fact log, capital/treasury, RCB, Constitution (**Phases 2–7**).
3. Deploy signed kernel pipeline, KERNEL-A, vault, MT5 bridge, OMS, recon, execution guards (**Phases 8–14**).
4. Deploy halt/kill, check-in, **control-api**, **notifier-bot**, monitoring/DR, Windows host (**Phases 15–19**).
5. Run strategy + cognitive SIM loop; adequacy engine + scenario harness (**Phases 20–22**).
6. Accumulate **≥6 months** SIM evidence (**Phase 23**).
7. Complete broker/compliance package and **§19** verification suite (**Phases 24–25**).
8. Arm LIVE: web passkey → arming delay → Telegram code in web (**§4.3**, **OI-TG-01**) → safe window — **Phase 26**.
9. Ramp **0.25×**, shadow twin, steady LIVE-L1 (**Phase 27**); **EUR/USD only** (**§5.1**, Appendix A `[universe] LIVE-L1`).

---

## 8. Security and continuity (deployment gates)

| Topic | Requirement | Blocks LIVE when |
|-------|-------------|------------------|
| Kernel artifact | Reproducible build, signed, red-team suite (**§8.3**, **A-P0-19**) | Suite fails or unsigned deploy |
| Constitution | Signed, version pinned (**A-CON-01**) | Invalid/expired |
| Broker verification | Written evidence for Kenya-resident Exness account (**§7.4**, **A-DEC-10**) | Unknown rules enabled |
| RPO/RTO | Harness built; numeric targets (**A-DEC-09**, §14.2) | Targets unset |
| Emergency relay | Policy (**A-DEC-08**, Telegram **OI-TG-03**) | Production control plane incomplete |
| Backups | Monthly restore on clean host (**§14.2**, **A-P0-18**) | Drill failed |

---

## 9. Cost and treasury (A-only)

- Tag costs **A**, **B**, or **GLOBAL** (**A-TRE-01**). In A-only, most infra is **GLOBAL** until B exists; allocate per **A-DEC-05** (starting: pro-rata by RCB — with B RCB = 0, document explicit interim rule in decision log).
- Owner bridge funding **$60/month combined** (**A-TRE-06**) — record as owner-paid; does not change RCB (**A-DEC-06** open).
- Withdrawals: **manual** Exness portal (**§7.3**, **§10.5**; verify by **implementation Phase 23/27**).

---

## 10. Definition of done for “independent deployment”

Independent deployment is achieved when:

1. **Architecture (§19):** Authority boundaries match §2.5–2.6; B absence does not weaken A controls.
2. **INV-01–INV-11** (§16.3) pass in CI and staged SIM environment.
3. **Kill drills (A-KIL-06):** K1–K3 exercised via Telegram, web, and signed CLI in SIM.
4. **Partial halt** displays correctly with B not deployed (**TG-T-08**).
5. Group A **SIM** runs continuously with reconciliation (**A-SIM-02** path) without any Group B binary running.

After this, **Phase 23** accumulates **SIM-adequacy** calendar evidence; **Phases 24–27** address compliance, **§19** LIVE eligibility, entry, and steady LIVE-L1.
