# Data, audit, fact log, and decision journal

**Source:** Group A §12; **A-LOG-***; Appendix B event classes.

---

## 1. Event envelope (§12.1)

Every Group A event includes:

`event_id`, `event_type`, `group_scope`, `occurred_at`, `recorded_at`, `correlation_id`, `source`, payload hash, `schema_version`, `previous_hash`, provenance reference.

**Event classes:** orders; fills; positions; broker balances; capital-state transitions; RCB changes; Constitution versions; signatures; deployments; halts; reimbursements; invoices; alerts; model versions; advisory signals; state transitions; reconciliations; failures; owner actions; check-ins.

Telegram sends also logged: message ID, principal, scope, category, severity, resulting event (TG principle 4).

---

## 2. Immutability and replay (§12.2)

| ID | Rule |
|----|------|
| **A-LOG-01** | Append-only; corrections = compensating events |
| **A-LOG-02** | Unique idempotent event IDs; broker + local timestamps |
| **A-LOG-03** | Correlation IDs link intent → verdict → order → broker order → fill → recon |
| **A-LOG-04** | Cold storage/compression OK if audit reconstructable; decision docs retained by reference |
| **A-LOG-05** | CRC32 + previous hash; audit explorer verifies chain; replay state at time T |
| **A-LOG-06** | Write failure → block/degrade by criticality; **never fabricate** |

Fact-log write failure → Telegram ERROR CRITICAL (ALL) per TG spec §6.12.

---

## 3. Decision journal (§12.3)

Per Group A decision **before** action:

- Information available (as-of), hypothesis, advisory inputs, risks, expected return/downside, action/abstention, verdict reference.

After outcome known:

- Outcome, attribution (direction, carry, costs, luck), assumptions held?

Reviews feed promotion gates; **never** change live parameters directly.

Web **Journal and Why** pages; Telegram `/why <id>` — fact-log-only prose (**TG-12**).

---

## 4. Retention (§12.4)

| Data | Retention | Notes |
|------|-----------|-------|
| Group A ticks | 90d (stripped profile: 14d) | Bars kept longer |
| Bars | 5 years | Compress after 30d |
| Orders, fills, verdicts, equity snapshots | Indefinite | Tax/attribution |
| Fact log, journal, advisory signals | Indefinite | Hash-chained; encrypted off-host backup |
| LLM prompts/responses | 12 months | Advisory audit |
| Logs/traces | 30d / 14d | Operational |

---

## 5. Storage architecture (design)

| Store | Role |
|-------|------|
| Fact log service | Authoritative append-only chain |
| Operational DB | Projections (capital, orders, RCB) — rebuildable from log |
| Object storage | Cold archive, backups |

**A-P0-02:** Hash chain, A scope, all §12.1 classes.

Restore drill: validate chain → replay → reconcile broker (§14.2).

---

## 6. Audit explorer (web §13.3)

- Hash-chain verification UI.
- Replay to timestamp T.
- Notification history cross-link.

Tests: DR class §16.1; TG-T-12 for /why numeric links.
