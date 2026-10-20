# Monitoring, backup, and continuity

**Source:** Group A §14; **A-P0-17**, **A-P0-18**; **A-DEC-09**; Appendix D.

---

## 1. Observables (§14.1)

All metrics/alerts: **timestamp + group_scope=A** (or ALL for infra).

| Domain | Examples |
|--------|----------|
| Kernel | Heartbeat, verdict latency p99, halt/kill state |
| Broker | Adapter state §7.2, fingerprint, poll failures |
| Market data | Freshness, latency |
| Reconciliation | Clean/mismatch, last run |
| Risk | Drawdown, floor proximity, margin |
| Capital | RCB, ratified vs equity |
| Treasury | Obligations, deadlines, reimbursement state |
| Deployment | Artifact hash, Constitution version |
| Security | Signature verification failures, key expiry |
| Fact log | Chain integrity |
| Backup | Last success/failure |
| Check-in | Days since presence |

**No silent recovery.**

### 1.1 Alert severity (§14.1)

| Severity | Examples | Suppression |
|----------|----------|-------------|
| **CRITICAL** | Kernel bypass hint; wrong fingerprint; global halt uncertainty; fact-log integrity failure; key compromise | **Never** flood-suppressed |
| **HIGH** | Broker outage; recon mismatch; cash-floor risk; RCB anomaly; missed treasury deadline | Deduplicated; retained |
| **NOTICE** | Cost cap warning; approaching threshold; minor degradation | May rate-limit with audit record |

Maps to Telegram HEALTH/ERROR/HALT where proactive notify enabled.

Constitution `quiet_hours_utc` (e.g. 20:00–04:00): CRITICAL bypasses (**TG-07**).

---

## 2. Backup and recovery (§14.2)

| Scenario | Procedure | Evidence |
|----------|-----------|----------|
| Database loss | Restore latest verified backup; validate hash chain; replay; reconcile broker | Monthly restore drill |
| Host failure | Approved image/artifact; verify signatures; reconcile before resume | Recovery drill |
| Broker outage | Do not invent state; preserve last known; wait; broker playbook | Outage drill |
| Kernel failure | Broker stops protect; no new risk | Failure injection |
| Owner absence | Dead-man MANAGE_ONLY → flatten | Timer drill |
| Owner incapacity | Trusted contact kill-only | Kill-only drill |
| Estate continuity | Sealed runbook | Annual review |
| Emergency relay | Signed risk-reducing path only (**A-DEC-08**) | Security drill |

**Backups:** encrypted, off-host, **monthly restore on clean host**. Restored config **never** live without verification.

**A-DEC-09:** Numeric **RPO/RTO** not frozen — build harness + evidence schema first; **LIVE gate blocked** until set.

---

## 3. Monitoring integration

| Component | Emits | Consumes |
|-----------|-------|----------|
| KERNEL-A | heartbeat, halt level, check-in timer | — |
| mt5-bridge | adapter state, latency | — |
| fact log | chain head, write errors | backup jobs |
| control-api | auth failures, scope violations | alerts |
| notifier-bot | delivery failures | TG-PO-15 templates |

Telegram TG-PO-15: health/error notification templates.

---

## 4. Windows host ops (BF-A3)

Schedule updates/restarts outside trading windows; on restart kernel reloads halt state from disk, reconciles before risk-increasing resume.

See [06-broker-exness-mt5.md](./06-broker-exness-mt5.md), [independent-deployment-strategy.md](./independent-deployment-strategy.md).
