# SATE (Sata)

**Sovereign Autonomous Trading Ecosystem** — a private, owner-operated system for automated trading under limits you commit in advance and a compiled safety kernel enforces. This repository holds requirements, design, and (over time) implementation for SATE.

**Owner:** Kennedy (sole operator and sole user). **Classification:** private — no credentials belong in this repo.

The authoritative requirements live in [`docs/source/`](docs/source/). Engineering design for the first delivery track is in [`docs/design/group_a/`](docs/design/group_a/).

---

## What SATE is for

SATE exists so one owner can run **two independent trading programs** with:

- **Deterministic risk and execution** — strategies propose *intents*; a **Rust kernel** returns a *verdict* before anything reaches a broker.
- **Signed limits** — a **Constitution** caps universe, sizing, drawdown, modes, and treasury rules; the kernel refuses unsigned or invalid config.
- **Full auditability** — an append-only, hash-chained **fact log** records orders, fills, halts, owner actions, and advisory inputs so every decision can be replayed and explained (`/why` in Telegram, journal in the web app).
- **Fail-closed safety** — halts (L1–L4), owner **kill switch** (K1–K3), broker-side **protective stops**, reconciliation against the broker as source of truth, and check-in / dead-man de-risking if the owner goes quiet.
- **Advisory AI, not autonomous AI** — a **cognitive plane** may publish signed advisory signals; it has **no** order, sizing, credential, or kernel authority. If advisory input is missing or invalid, the deterministic path uses a **zero view** and may abstain.

SATE is **not** a generic trading bot framework. It is a complete operating model: capital accounting, treasury, LIVE gates, runbooks, and verification suites defined in the system documentation.

*The source documents state clearly: they define design intent, not financial or legal advice. Leveraged trading can lose more than deposited capital.*

---

## Two groups, one ecosystem

Group A and Group B are **separate economic and execution domains**. They share notification, reporting, and coordination services, but **reporting may aggregate; control logic may not**. Combined balances are **reporting-only** and must never drive sizing, RCB, or LIVE eligibility for either group.

| | **Group A** | **Group B** |
|---|-------------|-------------|
| **Role** | Short-horizon leveraged engine (FX, metals, selected crypto CFDs) | Long-term unleveraged compounding (US equities & ETFs) |
| **Broker** | Exness via **MT5** (Windows host + Python bridge) | **Alpaca** (paper/live); IBKR planned as fallback |
| **Reference capital floor** | $500 RCB (necessary, never sufficient) | $200 RCB |
| **Modes** | SIM → **LIVE-L1/L2/L3** (+ MANAGE_ONLY, HALTED) | SIM → **LIVE-BMIN** / **LIVE-BFULL** |
| **Strategy sketch** | Kalman (+ regime), Black–Litterman with optional advisory; risk-budget sizing | **B-minimal** fixed-weight ETFs; **B-full** active allocation behind a validation gate |

Each group has its own broker profile, capital ledger, ratified capital base (**RCB**), Constitution, kernel, halt state, treasury ledger, and path to **LIVE eligibility**. Neither group needs the other to trade or to qualify for LIVE.

**Current build focus:** [Group A](docs/design/group_a/README.md) first, with an [independent deployment strategy](docs/design/group_a/independent-deployment-strategy.md) so Group A can run to SIM and LIVE while Group B is not yet deployed.

---

## How a trade is supposed to work (Group A)

High-level path from the Group A system documentation (§6.1):

```
Market data → signals (deterministic + optional advisory) → Intent
  → KERNEL-A (checks: halt, fingerprint, mode, RCB, risk, margin, …)
  → Verdict (Allow | AllowWithSize | Reject | Throttle)
  → order manager → MT5 bridge → broker
  → fills / reconciliation → fact log
```

No broker order without a valid kernel verdict. Credentials stay in the kernel; Telegram and the web app are **reduce-only** for fast stops (halt, flatten, kill, switch to SIM) — resume and SIM→LIVE require the **web app** and **passkey** re-authentication.

---

## Shared surfaces

| Surface | Purpose |
|---------|---------|
| **Web control plane** | Private SPA (passkey): Constitution, capital, eligibility, arming LIVE, resume, treasury, audit |
| **Telegram** | Always-with-owner notifications and **reduce-only** controls; scope tags `[A-LIVE]`, `[B-SIM]`, `[ALL]` — spec in [`docs/source/SATE_Telegram_Interface_Specification.docx`](docs/source/SATE_Telegram_Interface_Specification.docx) |
| **Signed CLI** | Out-of-band kill commands if web and Telegram are unavailable |
| **Halt coordinator** | K1–K3 and ALL-scope halt with explicit partial confirmation (never infer “all halted” from an unreachable kernel) |

---

## LIVE is not a feature flag

Going **LIVE** is allowed only when **that group alone** passes gates: capital/RCB, months of **SIM-adequacy** evidence, reconciliation history, broker verification, signed Constitution and kernel, preflight checklist, and operational drills (Group A §19). Flipping an environment variable or deploy flag is not sufficient.

---

## Documentation map

| Location | Contents |
|----------|----------|
| [`docs/source/SATE_Group_A_System_Documentation.docx`](docs/source/SATE_Group_A_System_Documentation.docx) | Group A requirements, scenarios, verification, backlog |
| [`docs/source/SATE_Group_B_System_Documentation.docx`](docs/source/SATE_Group_B_System_Documentation.docx) | Group B (future track; independence rules apply now) |
| [`docs/source/SATE_Telegram_Interface_Specification.docx`](docs/source/SATE_Telegram_Interface_Specification.docx) | Shared Telegram bot behaviour and tests |
| [`docs/design/group_a/`](docs/design/group_a/) | Full Group A design spec (15 subsystem docs + Telegram + phases + traceability); start at [`group_a/README.md`](docs/design/group_a/README.md) |

Open **implementation blockers** (owner decisions required before engineering may assume values) are tracked in [`docs/design/group_a/decision-log.md`](docs/design/group_a/decision-log.md) (Group A §20, Telegram open items).

---

## Repository status

Requirements and implementation **design** are in place for Group A; application code will follow the phased plan in [`docs/design/group_a/implementation-phases.md`](docs/design/group_a/implementation-phases.md). Group B design package is not started in this repo yet.
