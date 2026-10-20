# Operational scenarios and runbooks

**Source:** Group A §15 (all scenario families), Appendix C runbooks.

Each scenario specifies **trigger**, **system behaviour**, **owner role**, and **outcome** differently — implement as executable tests (§16) and runbook steps (Appendix C).

---

## 1. Trading scenarios (§15.1)

| ID | Trigger (summary) | System behaviour | Owner |
|----|-------------------|------------------|-------|
| TS-01 | Kalman innovation exceeds threshold; instrument in rung universe | BL blend if valid; size §5.3; intent→kernel; on Allow: order+broker stop; journal before act | None — manage via stops |
| TS-02 | Advisory plane unavailable | Zero advisory view; Kalman continues | None |
| TS-03 | Weak/conflicting/stale evidence or tool fail | ABSTAIN + reason; zero view; digest | None |
| TS-04 | Min lot exceeds risk budget | Reject `untradeable_at_this_capital`; floor rules if applicable | None |
| TS-05 | Kernel reject (risk, notional, concentration, margin, blackout, swap, universe) | Reject w/ values; no order | None |
| TS-06 | Size fits reduced limit | AllowWithSize | None |
| TS-07 | Rate limit | Throttle | None |
| TS-08 | News blackout window | Reject inside window | None |
| TS-09 | Swap-cost guard (incl. Wed triple) | Reject or Constitution exit rule | None |
| TS-10 | Stale ticks | No new risk; freshness logged; L1/L2 by severity | None |
| TS-11 | Duplicate intent / timeout | Existing outcome; reconcile before retry | None |
| TS-12 | Partial fill | Partial-fill event; remainder state; stop on filled qty | None |
| TS-13 | Protective stop cannot be placed | Do not open; log | None |

**Design tests:** UT/IT/REC + Group A §16.2 swap/blackout tests.

---

## 2. Automatic halts (§15.2)

| ID | Trigger | Behaviour | Owner |
|----|---------|-----------|-------|
| HL-01 | L1 slippage > 20-trade budget | Half size; widen thresholds; notify | Auto exit L1 |
| HL-02 | L1 feed degraded | L1; escalate L2 if severe | Auto |
| HL-07 | L3 drawdown breach | Flat/hedge then stop | Re-arm |
| HL-08 | L3 margin stress | Same as HL-07 | Re-arm |
| HL-A | L2 daily loss limit | Block new risk; manage; RCB cool-off; pause injections | Auto next session |
| HL-B | L2 recon mismatch | Block; no retry; identify diff; correct from broker | Auto after clean recon |
| HL-C | L2 fingerprint mismatch on connect | Halt; refuse orders until verified | Resume after clean recon |
| HL-D | L2 kernel/feed heartbeat lost | Fail closed; restart; reload halt; verify stops | Auto after restart |
| HL-E | Repeated L2 | Escalate L3 | Re-arm |
| HL-F | L4 ops heartbeat / unexplained account change | Flatten; revoke kernel trading access | Re-provision |

Post L3/L4: not same-day resume; pre-mortem; tighten Constitution; ramped return (§15.2 narrative).

---

## 3. Owner controls (§15.3)

| ID | Trigger | Behaviour | Owner |
|----|---------|-----------|-------|
| OC-01 | K1 for A | No new entries; manage w/ stops | Invoke; later re-arm |
| OC-02 | K2 for A | Cancel pending; close all; stop | Invoke; confirm; re-arm |
| OC-03 | K3 for A | K2 + seal credentials | Re-provision; SIM→LIVE path |
| OC-04 | ALL kill, one kernel unreachable | HALT_REQUESTED; partial ack only | Escalate runbook/portal |
| OC-05 | Web+TG down | Signed CLI; else broker portal manual | Invoke |
| OC-06 | Trusted contact kill | K1–K3 only | Re-arm later |
| OC-07 | Resume after K1/K2 | Web passkey, cool-off, recon, preflight | Re-arm |
| OC-08 | Resume after K3 | Re-provision + SIM→LIVE | Re-provision |

---

## 4. Account modes (§15.4)

See [03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md) for AM-01–AM-A7 detail.

---

## 5. Capital and treasury (§15.5)

See [02-capital-rcb-treasury.md](./02-capital-rcb-treasury.md) for CT-01–CT-A1.

---

## 6. Owner presence (§15.6)

| ID | Trigger | Behaviour | Owner |
|----|---------|-----------|-------|
| OP-01 | Day 7 no check-in (LIVE) | Telegram+email reminders | /alive or web |
| OP-02 | Day 10 | MANAGE_ONLY | Check in; lift in web |
| OP-03 | Day 14 | Flatten LIVE; stop | Re-arm flow |
| OP-04 | Planned absence | Away mode extends timers | Web passkey completion |
| OP-05 | SIM during lapse | SIM continues | None |
| OP-06 | Telegram takeover | Reduce-only; increase needs web passkey | Rotate bot token |

---

## 7. Broker and infrastructure (§15.7)

| ID | Trigger | Behaviour | Owner |
|----|---------|-----------|-------|
| BF-01 | Broker API down | No blind retry; UNAVAILABLE; stops remain | Reconcile before resume |
| BF-02 | Broker terms change | L1/L2 until understood; rerun cost model | Review gates |
| BF-03 | Withdrawals frozen/delayed | Stop adding capital; reduce exposure | Cap balance; escalate |
| BF-04 | Insolvency/regulatory | K2 if possible; no new deposits | Claims process |
| BF-05 | Outage + open positions | Rely on broker stops | Reconcile |
| BF-06 | Protective order rejected | No open; server-side fallback only if verified | None |
| BF-07 | Kernel failure | Fail closed | Restart/reconcile |
| BF-08 | LLM/memory fabric down | Abstain; zero/cached view | None |
| BF-09 | Network partition/host loss | Halt; reconcile before resume | None |
| BF-A1 | MT5/bridge crash | Watchdog restart; pause until reconciled | None |
| BF-A2 | Leverage/spread change | Recompute margin; L1/L2 until understood | Review |
| BF-A3 | Windows update/restart | Reconcile before resume | None |

---

## 8. Model updates (§15.8)

| ID | Trigger | Behaviour | Owner |
|----|---------|-----------|-------|
| MP-01 | Challenger passes gate | Promote next safe window; probation | None |
| MP-02 | Challenger fails | Discard; champion continues | None |
| MP-03 | Probation underperforms | Auto rollback | None |

Promotion statistics: §15.8 narrative in [04-strategy-quant-engine.md](./04-strategy-quant-engine.md).

---

## 9. Appendix C runbooks (operational steps)

| Runbook | When | Primary doc |
|---------|------|-------------|
| **C.1** Kill switch invoked | After any K1–K3 | [08-halts-kill-checkin.md](./08-halts-kill-checkin.md) |
| **C.2** Kernel heartbeat lost | HL-D | [05-kernel-oms-reconciliation.md](./05-kernel-oms-reconciliation.md) |
| **C.3** Reconciliation mismatch | HL-B | [05-kernel-oms-reconciliation.md](./05-kernel-oms-reconciliation.md) |
| **C.4** SIM → LIVE | AM-01 | [03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md) |
| **C.5** Recovery after L3/L4 | Post flatten | [08-halts-kill-checkin.md](./08-halts-kill-checkin.md) |
| **C.6** Check-in lapsed | OP-01–03 | [08-halts-kill-checkin.md](./08-halts-kill-checkin.md) |
| **C.7** Broker failure | BF-* | [06-broker-exness-mt5.md](./06-broker-exness-mt5.md) |
| **C.8** Manual withdrawal | CT-05 | [02-capital-rcb-treasury.md](./02-capital-rcb-treasury.md) |
| **C.9** Reverse graduation | AM-A5 | [03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md) |
| **C.10** MT5 terminal crash | BF-A1 | [06-broker-exness-mt5.md](./06-broker-exness-mt5.md) |

### C.1–C.10 step lists (source Appendix C)

**C.1 Kill:** (1) Confirm kill finished on TG/web vs broker portal. (2) Compare portal to system. (3) Fact log review + cause. (4) Resume via web; K3 → re-provision first.

**C.2 Heartbeat:** (1) Fail closed; check TG L2. (2) Restart kernel; reload halt; query broker. (3) Reconcile; verify stops. (4) Manual portal if kernel won't start.

**C.3 Recon mismatch:** (1) L2 automatic; no order retry. (2) Identify diff. (3) Correct from broker; log root cause. (4) Resume after one clean recon.

**C.4 SIM→LIVE:** (1) Preflight + evidence. (2) Web passkey + arming wait. (3) Telegram code in web; safe window. (4) Ramp + shadow twin watch.

**C.5 L3/L4 recovery:** (1) Not same day. (2) Pre-mortem. (3) Tighten Constitution. (4) Web re-arm + ramp.

**C.6 Check-in:** (1) Day 7 `/alive` or web. (2) Day 10 MANAGE_ONLY → check in lift. (3) Day 14 flattened → C.5.

**C.7 Broker failure:** §15.7; stops; log broker comms.

**C.8 Withdrawal:** NOTICE → reduce exposure → portal → web confirm → reconcile RCB.

**C.9 Reverse grad:** WARN; MANAGE_ONLY; no rush deposit; 14d re-entry block; full preflight.

**C.10 MT5 crash:** Watchdog; reconcile; portal fallback.
