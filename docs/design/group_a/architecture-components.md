# Group A — Architecture and Components

Maps the **logical architecture** for implementation to Group A system documentation sections. This is the component view engineers implement; the **independence contract** remains in [independent-deployment-strategy.md](./independent-deployment-strategy.md).

**Primary references:** Group A §2 (overview), §2.6 (shared services), §6.1 (control path), §7 (broker), §8 (Constitution/deploy), §12 (fact log), §13 (interfaces).

---

## 1. Component catalogue

| Component | Language / runtime | Authority | Holds secrets | Source |
|-----------|-------------------|-----------|---------------|--------|
| **KERNEL-A** | Rust (compiled) | Final verdict on every intent; halt/kill; credential custody | Exness trade keys | §6.3, A-KRN-01–08 |
| **MT5 bridge** | Python + thread pool | Normalise broker I/O; no trading decisions | None (requests via kernel) | §7.3 |
| **MT5 terminals** | Windows (Exness) | Broker UI/API surface | Session via kernel only | §7.3 |
| **Strategy engine** | Python (typical) | Produce **Intents** only | None | §5, §6.2 |
| **Regime / Kalman / BL** | Python | Deterministic signals | None | §5.2–5.3 |
| **Order manager (OMS)** | Rust or Python under kernel policy | Idempotency, lifecycle | None | §6.5, A-OMS-01–05 |
| **Reconciliation worker** | Service | Broker source of truth → state projection | Read-only broker access via kernel | §6.6, A-REC-01–04 |
| **Fact log service** | Service + storage | Append-only audit | Signing keys for log integrity (not trade) | §12, A-LOG-01–06 |
| **Capital ledger** | Service | Five-state capital model | None | §3.2, A-P0-04 |
| **RCB service** | Service | Ratification, cool-off, effective limits | None | §3.4, A-RCB-01–08 |
| **Treasury ledger** | Service | Obligations, reimbursement state machine | None | §10, A-TRE-, A-OBL- |
| **Constitution store** | File + DB metadata | Signed config artifact | Verify keys pinned | §8, Appendix A |
| **Halt coordinator** | Service | K1–K3 propagation; ALL-scope protocol | Limited control auth | §9.1–9.3 |
| **control-api** | Service | Scope enforcement; arming/resume | Session/WebAuthn verification | §13.2 |
| **dashboard-api** | Service (optional split) | Read models, reporting-only aggregates | None | §13.3 |
| **Web SPA** | React/TS | Presentation; not security boundary | None | §13.3 |
| **notifier-bot** | Python (aiogram/python-telegram-bot) | Telegram UX; reduce-only | Bot token + limited control token | Telegram spec §13 |
| **Cognitive plane** | Separate service | Signed AdvisorySignal | Reasoning graph signing key | §11 |
| **Market-data ingestion** | Service | Freshness-tagged ticks/bars | Vendor keys | §2.6, §6.7 |
| **Monitoring / alerting** | Service | Metrics, CRITICAL path | None | §14.1 |
| **Backup agent** | Job | Encrypted off-host backup | Backup encryption keys | §14.2 |
| **Signed CLI (kill)** | Tool | Out-of-band K1–K3 to kernel local channel | Ed25519 kill key material | §9.2 |

---

## 2. End-to-end control path (Group A §6.1)

```
MT5 ticks + calendar
  → data validation / freshness (stale ⇒ no new risk §6.7)
  → Kalman + regime (§5.2)
  → AdvisorySignal optional (§11) → Black-Litterman (§5.2)
  → sizing → Intent (§6.2)
  → pre-kernel validation (group scope A)
  → KERNEL-A checks §6.4 order
  → Verdict: Allow | AllowWithSize | Reject | Throttle
  → OMS → MT5 bridge (ZeroMQ) → terminal → Exness
  → fills / positions → fact log + reconciliation
```

**Invariant:** No path from cognitive plane or web/Telegram to broker without kernel verdict (**INV-01**, **A-COG-01**).

---

## 3. Kernel check order (§6.4)

Implement as ordered, short-circuiting pipeline:

1. Kill and halt state (**A-KRN-06**)
2. Account fingerprint (**A-MOD-02**)
3. Mode and state (SIM / LIVE-L1…L3, universe, ramp)
4. RCB and ratified limits — `min(RCB, equity)` (**A-RCB-01**)
5. Drawdown (daily, peak)
6. Per-trade risk budget + minimum lot (**A-SZ-02**, A-DEC-01)
7. Open notional and leverage used
8. Concentration
9. Margin level
10. News blackout and swap-cost guard (**A-EXE-02**)
11. Rate limit

Verdict payload: **Appendix B** `Verdict` schema.

---

## 4. Mode and state machine (§4.1)

| State | Kernel/trading behaviour |
|-------|---------------------------|
| **SIM** | Simulated/live demo account; intents against demo profile |
| **LIVE-L1** | Ramped live; reduced universe (EUR/USD start); shadow twin |
| **LIVE-L2 / L3** | Blocked until **A-DEC-02** — implement transitions but gate disabled |
| **MANAGE_ONLY** | No new risk-increasing entries |
| **HALTED** | L2+ or kill; recovery per §15 |

Mode transitions: **§4.3** (SIM→LIVE), **§4.4** (LIVE→SIM), ladder **§4.5** (A-LAD-, A-SIM-).

---

## 5. Broker adapter (§7.1–7.3)

**Adapter states:** DISCONNECTED → AUTHENTICATING → UNVERIFIED → HEALTHY | DEGRADED | RECONCILING | UNAVAILABLE (**§7.2**). Non-healthy ⇒ block risk-increasing orders.

**Group A specifics:**

- Synchronous MT5 Python calls isolated in bridge process (**§7.3**).
- Separate demo/live portable terminals.
- 5-second read poll + immediate fill handling (**A-KRN-03**).
- Protective stop on every entry (**A-EXE-03**, **A-P0-13**).

---

## 6. Persistent entities (Appendix B)

Implement storage for at minimum:

`AccountProfile`, `CapitalSnapshot`, `RCBState`, `Constitution`, `Intent`, `Verdict`, `Order`, `Fill`, `Position`, `TreasuryObligation`, `Reimbursement`, `HaltCommand`, `OwnerAction`.

All trading entities carry **`group_id = A`**.

---

## 7. External interfaces

### 7.1 control-api (§13.2)

| Endpoint | Scope | Notes |
|----------|-------|-------|
| `GET /state` | A (and read B when exists) | Mode, halt, heartbeat, capital states |
| `POST /kill` | A, B, ALL | Risk-reducing |
| `POST /mode/A/sim` | A | LIVE→SIM |
| `POST /mode/A/arm` | A | Passkey + preflight |
| `POST /mode/A/confirm` | A | OTP from Telegram → web only |
| `POST /resume/A` | A | Reconciliation + cool-off |
| `POST /checkin`, `/checkin/away` | Presence | Not risk-increasing |
| `POST /capital/ratify` | A | 14-day clean + passkey |

### 7.2 Telegram (full spec in source doc)

Implement per Telegram spec §3–10, §13; Group A summary **§13.4**, **A-TG-01–06**. Bot process **`notifier-bot`** — Telegram spec §13.1.

---

## 8. Observability (§14.1)

Emit with `group_scope=A`:

- Kernel heartbeat, verdict latency (A-KRN-07 target)
- Adapter state, fingerprint status
- Reconciliation status, drawdown, floor proximity (**A-LAD-01**)
- RCB, treasury obligations, check-in timer
- Fact-log chain integrity
- Deployment artifact hash / Constitution version

**CRITICAL** alerts: kernel bypass suspicion, wrong account, global halt uncertainty, fact-log integrity failure, key compromise — never suppressed (**§14.1**).

---

## 9. Technology constraints (from requirements)

| Constraint | Detail |
|------------|--------|
| Kernel hot path | p99 &lt; 1 ms, no heap alloc on hot path (**A-KRN-07**) |
| Kernel IPC | Local socket or named pipe; separate process |
| Web | Private network; WebAuthn; CSP; CSRF on controls (**§13.3**) |
| Time | UTC / New York for market rules (**§1.4**) |

---

## 10. Group B placeholder interfaces

Until Group B exists:

- Halt API accepts `scope=B` requests but returns **unreachable** / no-op ack with explicit status (never success for ALL).
- Reporting API returns `group_b: not_deployed`.
- No shared “total equity” field on any kernel or sizing API (**INV-03**).

When Group B is added, same APIs gain a second kernel registration without changing A contracts (**A-IND-03**).
