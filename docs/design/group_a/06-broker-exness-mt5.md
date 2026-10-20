# Broker integration — Exness MT5

**Source:** Group A §7; scenarios §15.7 (BF-*); Appendix D.

---

## 1. Adapter contract areas (§7.1)

| Area | Implementation requirement |
|------|---------------------------|
| Authentication | Credentials only inside kernel boundary; rotate via security runbook |
| Account fingerprint | Read-only identity check pre-LIVE + continuous |
| Market data | Normalised prices + source timestamps + freshness |
| Order submission | Kernel-approved only; mandatory idempotency key |
| Order status | Normalised states; preserve raw broker IDs |
| Fills | Partial/full, fees, timestamps |
| Positions | Periodic + event snapshots; broker truth |
| Balances/cash | Equity, margin, settlement fields for account type |
| Settlement | Account-specific; unknown rule → block capability |
| Withdrawals | Eligibility if API exists; else **manual owner workflow** |
| Fees | Explicit fee records + currency |
| Server time | On every relevant event; **NTP** on hosts |
| Outage/rate limits | Health + backoff; no blind duplicate submit |
| Reconciliation | Daily minimum + event-driven |

---

## 2. Adapter state machine (§7.2)

Adapter state ≠ trading mode. Non-healthy **never** permits risk-increasing orders.

| State | Meaning | Risk-increasing orders |
|-------|---------|------------------------|
| DISCONNECTED | No broker session | Blocked |
| AUTHENTICATING | Credential exchange in kernel | Blocked |
| UNVERIFIED | Fingerprint/capability pending/failed | Blocked |
| HEALTHY | Auth OK, fingerprint OK, fresh data, heartbeat | Subject to kernel verdict |
| DEGRADED | Stale/rate limit/late heartbeat | Blocked until HEALTHY |
| RECONCILING | Post-outage/discrepancy compare | Blocked until clean |
| UNAVAILABLE | Outage/maintenance | Blocked; preserve last known state |

Expose state to monitoring (§14.1) and web System health page.

---

## 3. Group A specifics (§7.3)

| Aspect | Design |
|--------|--------|
| Connection | MT5 terminal + **Python bridge**; sync MT5 API calls in **thread pool** separate process |
| IPC | **ZeroMQ** to strategy — **never** on strategy event loop |
| Terminals | **Separate portable** demo/live instances; kernel owns bridge; terminal reachable only from kernel |
| Host | **Windows**, near broker region; latency measured in SIM |
| Account | Raw/zero-spread + commission preferred; verify Kenya-resident eligibility |
| Swap | Daily **17:00 New York**, **triple Wednesday**; model + kernel guard |
| Leverage | Recompute margin headroom every poll; broker may change leverage without notice |
| Time | Broker server time on events; clock skew = red-team case (R-79) |
| Withdrawals | **Manual** Exness portal; no programmatic withdrawal assumed (Appendix D) |

---

## 4. Broker verification blocker (§7.4)

Before enabling affected **LIVE** capabilities, obtain written evidence for:

- Kenya-resident eligibility, account type, products, leverage.
- Withdrawal mechanics.
- Settlement and rule applicability.
- Protective order behaviour and rejection rules.

**Unknown rules stay disabled** (**INV-08**). Track in fact log with verification date (Appendix D). **A-DEC-10**.

---

## 5. MT5 bridge process model

```
┌─────────────────────────────────────────┐
│ KERNEL-A (Rust)                          │
│  - verdict, OMS, credential vault          │
│  - ZMQ REQ/REP or dealer to bridge       │
└─────────────────┬───────────────────────┘
                  │ ZeroMQ
┌─────────────────▼───────────────────────┐
│ mt5-bridge (Python, thread pool)         │
│  - MetaTrader5 package sync calls          │
│  - normalise to adapter contract           │
└─────────────────┬───────────────────────┘
                  │
     ┌────────────┴────────────┐
     ▼                         ▼
 demo terminal            live terminal
 (SIM profile)            (LIVE profile)
```

Watchdog: terminal crash → restart → execution paused until reconnect + reconcile (C.10, BF-A1).

---

## 6. Broker scenarios (§15.7)

| ID | Summary |
|----|---------|
| BF-01 | API unavailable → UNAVAILABLE, no blind retry |
| BF-02 | Terms change → L1/L2 until understood |
| BF-03 | Withdrawals frozen → reduce exposure, cap balance |
| BF-04 | Insolvency → K2 if possible; no new deposits |
| BF-05 | Outage + open positions → rely on broker stops |
| BF-06 | Stop rejected → no open; server-side fallback only if verified (see ambiguities doc) |
| BF-07 | Kernel failure → fail closed |
| BF-08 | LLM down → zero advisory |
| BF-09 | Network partition → halt, reconcile before resume |
| BF-A1 | MT5/bridge disconnect |
| BF-A2 | Leverage/spread change |
| BF-A3 | Windows update/restart → reload state, reconcile |

---

## 7. Appendix D dependencies (broker-related)

| Assumption | Verify | Blocks |
|------------|--------|--------|
| Exness types/leverage/products for Kenya resident | Broker docs + written support | Impl. **24–25** / LIVE |
| MT5 Python terms, VPS | Exness terms | Impl. **11**, **19** |
| Min lot, pip value, contract specs | Contract specs | A-DEC-01; **11**, **14** |
| Protective order behaviour | Docs + tests | Impl. **14**, **24–25** |
| Windows hosting cost | Provider pricing | Impl. **19** |
| Latency/slippage | SIM measurement | Impl. **11**, **20**, **23** |
| Programmatic withdrawal | Docs (assume none) | Impl. **23**, **27** |
