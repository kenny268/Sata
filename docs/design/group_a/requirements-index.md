# Group A — requirement ID index (132 `A-*`)

Machine-derived from Group A source text. **Normative wording** remains in the `.docx`. Each ID maps to the primary design document section that implements or constrains it.

| ID | Primary design doc | Summary (abbrev.) |
|----|-------------------|-------------------|
| A-CHK-01 | [08-halts-kill-checkin.md](./08-halts-kill-checkin.md) | A check-in is a passkey login to the web app or the /alive |
| A-CHK-02 | [08-halts-kill-checkin.md](./08-halts-kill-checkin.md) | Away mode extends the timers for a stated number of days up |
| A-CHK-03 | [08-halts-kill-checkin.md](./08-halts-kill-checkin.md) | The timer shall run in the kernel, independent of the |
| A-CHK-04 | [08-halts-kill-checkin.md](./08-halts-kill-checkin.md) | The trusted contact is not a substitute operator: delegated |
| A-CHK-05 | [08-halts-kill-checkin.md](./08-halts-kill-checkin.md) | At day 10 and day 14 the effect on Group A falls on open |
| A-COG-01 | [09-cognitive-plane.md](./09-cognitive-plane.md) | Group A shall use an advisory view of zero whenever no valid, |
| A-COG-02 | [09-cognitive-plane.md](./09-cognitive-plane.md) | c shall come from a calibration table fitted on past signals |
| A-COG-03 | [09-cognitive-plane.md](./09-cognitive-plane.md) | Retrieved text is data, not instruction; prompt injection, |
| A-COG-04 | [09-cognitive-plane.md](./09-cognitive-plane.md) | The advisory contribution shall be evaluated against the |
| A-CON-01 | [07-constitution-crypto-deployment.md](./07-constitution-crypto-deployment.md) | The kernel shall verify the Constitution signature, version, |
| A-CON-02 | [07-constitution-crypto-deployment.md](./07-constitution-crypto-deployment.md) | Edits shall take effect only after a time-lock; tightening |
| A-CON-03 | [07-constitution-crypto-deployment.md](./07-constitution-crypto-deployment.md) | Pending changes shall not activate silently; lock state and |
| A-CON-04 | [07-constitution-crypto-deployment.md](./07-constitution-crypto-deployment.md) | No approval workflow shall exist for individual trades; the |
| A-DEC-01 | [decision-log.md](./decision-log.md) | Per-trade risk cap vs minimum lot at $500 floor |
| A-DEC-02 | [decision-log.md](./decision-log.md) | LIVE-L2/L3 rungs and graduation parameters |
| A-DEC-03 | [decision-log.md](./decision-log.md) | SIM-adequacy return hurdle (6% vs cost-derived) |
| A-DEC-04 | [decision-log.md](./decision-log.md) | Constitution tighten/loosen time-lock hours |
| A-DEC-05 | [decision-log.md](./decision-log.md) | Shared-cost allocation when use is asymmetric |
| A-DEC-06 | [decision-log.md](./decision-log.md) | End of temporary funding bridge per group |
| A-DEC-07 | [decision-log.md](./decision-log.md) | Windows MT5 host choice (VPS vs owned vs broker) |
| A-DEC-08 | [decision-log.md](./decision-log.md) | Emergency relay endpoint, auth, replay policy |
| A-DEC-09 | [decision-log.md](./decision-log.md) | Numeric RPO and RTO targets |
| A-DEC-10 | [decision-log.md](./decision-log.md) | Kenya Exness broker and tax verification |
| A-EXE-01 | [04-strategy-quant-engine.md](./04-strategy-quant-engine.md) | Spread, commission, swap (including triple swap on Wednesday) |
| A-EXE-02 | [04-strategy-quant-engine.md](./04-strategy-quant-engine.md) | A swap-cost guard and the news blackout windows shall be |
| A-EXE-03 | [04-strategy-quant-engine.md](./04-strategy-quant-engine.md) | Every entry shall carry a broker-side protective stop; an |
| A-EXE-04 | [04-strategy-quant-engine.md](./04-strategy-quant-engine.md) | A breach of the slippage budget over the rolling 20-trade |
| A-FEE-01 | [02-capital-rcb-treasury.md](./02-capital-rcb-treasury.md) | Broker trading fees, commissions, swaps and slippage shall |
| A-FEE-02 | [02-capital-rcb-treasury.md](./02-capital-rcb-treasury.md) | Withdrawal fees and currency-conversion costs shall be |
| A-FEE-03 | [02-capital-rcb-treasury.md](./02-capital-rcb-treasury.md) | Every obligation shall have an owner, due date, currency, |
| A-FEE-04 | [02-capital-rcb-treasury.md](./02-capital-rcb-treasury.md) | An obligation due from the Group A broker shall be met from |
| A-FEE-05 | [02-capital-rcb-treasury.md](./02-capital-rcb-treasury.md) | Reporting currency treatment (USD broker balances against KES |
| A-IND-01 | [01-system-overview-independence.md](./01-system-overview-independence.md) | Every record carrying capital shall include scope = A (or |
| A-IND-02 | [01-system-overview-independence.md](./01-system-overview-independence.md) | Every calculation API for risk-bearing operations shall |
| A-IND-03 | [01-system-overview-independence.md](./01-system-overview-independence.md) | A state transition in Group A shall never mutate Group B |
| A-IND-04 | [01-system-overview-independence.md](./01-system-overview-independence.md) | Group A shall continue to operate, and shall keep its own |
| A-KIL-01 | [08-halts-kill-checkin.md](./08-halts-kill-checkin.md) | The kill switch shall work with the cognitive plane, |
| A-KIL-02 | [08-halts-kill-checkin.md](./08-halts-kill-checkin.md) | Halt, flatten, kill and LIVE-to-SIM shall be available from |
| A-KIL-03 | [08-halts-kill-checkin.md](./08-halts-kill-checkin.md) | Resume after K1 or K2 shall require re-arming from the web |
| A-KIL-04 | [08-halts-kill-checkin.md](./08-halts-kill-checkin.md) | The default scope of a command shall be Group A only; ALL |
| A-KIL-05 | [08-halts-kill-checkin.md](./08-halts-kill-checkin.md) | Every kill shall be a fact-log event recording channel, |
| A-KIL-06 | [08-halts-kill-checkin.md](./08-halts-kill-checkin.md) | Each phase gate shall trigger all three kill levels in SIM |
| A-KRN-01 | [05-kernel-oms-reconciliation.md](./05-kernel-oms-reconciliation.md) | The kernel shall validate every Group A intent before any |
| A-KRN-02 | [05-kernel-oms-reconciliation.md](./05-kernel-oms-reconciliation.md) | The kernel shall hold the trade-capable Group A credentials |
| A-KRN-03 | [05-kernel-oms-reconciliation.md](./05-kernel-oms-reconciliation.md) | The kernel shall poll the broker with a read-only key |
| A-KRN-04 | [05-kernel-oms-reconciliation.md](./05-kernel-oms-reconciliation.md) | The kernel shall attach protective orders with every entry |
| A-KRN-05 | [05-kernel-oms-reconciliation.md](./05-kernel-oms-reconciliation.md) | The kernel shall own Group A halt and kill state, persist it |
| A-KRN-06 | [05-kernel-oms-reconciliation.md](./05-kernel-oms-reconciliation.md) | The kernel shall read the kill and halt state before any |
| A-KRN-07 | [05-kernel-oms-reconciliation.md](./05-kernel-oms-reconciliation.md) | Verdict latency shall be under 1 ms at p99 with no heap |
| A-KRN-08 | [05-kernel-oms-reconciliation.md](./05-kernel-oms-reconciliation.md) | A failing safety check shall short-circuit risk-increasing |
| A-LAD-01 | [03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md) | On every broker poll the kernel shall raise a WARN when Group |
| A-LAD-02 | [03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md) | After 3 consecutive sessions below the floor (starting value) |
| A-LAD-03 | [03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md) | Re-entry shall require RCB recovery and the cool-off, shall |
| A-LAD-04 | [03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md) | A mode switch shall not be accepted during the ramp (ramp |
| A-LAD-05 | [03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md) | A Group A drawdown beyond a Constitution threshold during the |
| A-LAD-06 | [03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md) | Every graduation and reverse-graduation transition shall be |
| A-LOG-01 | [10-data-audit-fact-log.md](./10-data-audit-fact-log.md) | Append-only records are the audit authority; corrections are |
| A-LOG-02 | [10-data-audit-fact-log.md](./10-data-audit-fact-log.md) | Event IDs shall be unique and idempotency-safe; broker |
| A-LOG-03 | [10-data-audit-fact-log.md](./10-data-audit-fact-log.md) | Correlation IDs shall connect intent, verdict, order, broker |
| A-LOG-04 | [10-data-audit-fact-log.md](./10-data-audit-fact-log.md) | Cold storage may compress or archive data, but retained |
| A-LOG-05 | [10-data-audit-fact-log.md](./10-data-audit-fact-log.md) | Each entry carries a CRC32 and the previous hash; the audit |
| A-LOG-06 | [10-data-audit-fact-log.md](./10-data-audit-fact-log.md) | A fact-log write failure shall block or degrade according to |
| A-MOD-01 | [03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md) | Strategy and execution code shall be mode-agnostic: they |
| A-MOD-02 | [03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md) | At start-up, at every reconnect and at required intervals, |
| A-MOD-03 | [03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md) | Every fact-log entry, table row, metric and notification |
| A-MOD-04 | [03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md) | The web header shall show the Group A mode badge (LIVE in |
| A-MOD-05 | [03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md) | Live credentials shall not be present on a host or terminal |
| A-OBL-01 | [02-capital-rcb-treasury.md](./02-capital-rcb-treasury.md) | Treasury shall reduce Group A exposure ahead of an |
| A-OBL-02 | [02-capital-rcb-treasury.md](./02-capital-rcb-treasury.md) | If an obligation is due from the Group A broker and liquidity |
| A-OBL-03 | [02-capital-rcb-treasury.md](./02-capital-rcb-treasury.md) | Insufficient withdrawable cash shall defer the reimbursement |
| A-OMS-01 | [05-kernel-oms-reconciliation.md](./05-kernel-oms-reconciliation.md) | Every order submission shall carry a deterministic client and |
| A-OMS-02 | [05-kernel-oms-reconciliation.md](./05-kernel-oms-reconciliation.md) | A retry shall never be sent merely because a local request |
| A-OMS-03 | [05-kernel-oms-reconciliation.md](./05-kernel-oms-reconciliation.md) | A partial fill shall create an explicit lifecycle event; the |
| A-OMS-04 | [05-kernel-oms-reconciliation.md](./05-kernel-oms-reconciliation.md) | Cancellation shall be idempotent and reconciliation-backed |
| A-OMS-05 | [05-kernel-oms-reconciliation.md](./05-kernel-oms-reconciliation.md) | A duplicate intent shall return the existing outcome and |
| A-PERF-01 | [04-strategy-quant-engine.md](./04-strategy-quant-engine.md) | Success shall be net-of-all-costs return versus a passive |
| A-PERF-02 | [04-strategy-quant-engine.md](./04-strategy-quant-engine.md) | A strategy shall be retired to cash if, once the |
| A-PR-01 | [01-system-overview-independence.md](./01-system-overview-independence.md) | The LLM is advisory. Every number used downstream shall trace |
| A-PR-02 | [01-system-overview-independence.md](./01-system-overview-independence.md) | The kernel is the only holder of trade-capable Group A |
| A-PR-03 | [01-system-overview-independence.md](./01-system-overview-independence.md) | The broker is the source of truth for Group A balances, |
| A-PR-04 | [01-system-overview-independence.md](./01-system-overview-independence.md) | Abstention shall be a valid output at every reasoning and |
| A-PR-05 | [01-system-overview-independence.md](./01-system-overview-independence.md) | Actions that reduce risk shall be fast and easy; actions that |
| A-PR-06 | [01-system-overview-independence.md](./01-system-overview-independence.md) | Models and parameters shall change only through the promotion |
| A-PR-07 | [01-system-overview-independence.md](./01-system-overview-independence.md) | Only risk capital shall be traded: money the owner can afford |
| A-PR-08 | [01-system-overview-independence.md](./01-system-overview-independence.md) | Every decision shall be journaled before action and reviewed |
| A-RCB-01 | [02-capital-rcb-treasury.md](./02-capital-rcb-treasury.md) | Group A limits shall be computed on the Group A effective |
| A-RCB-02 | [02-capital-rcb-treasury.md](./02-capital-rcb-treasury.md) | If Group A equity falls below its RCB, effective limits shall |
| A-RCB-03 | [02-capital-rcb-treasury.md](./02-capital-rcb-treasury.md) | A withdrawal shall reduce the Group A RCB at once, and |
| A-RCB-04 | [02-capital-rcb-treasury.md](./02-capital-rcb-treasury.md) | An increase to the RCB, whether from a deposit, an injection |
| A-RCB-05 | [02-capital-rcb-treasury.md](./02-capital-rcb-treasury.md) | A qualifying L2, L3 or L4 event restarts the 14-day cool-off |
| A-RCB-06 | [02-capital-rcb-treasury.md](./02-capital-rcb-treasury.md) | A deposit during or after a halt shall remain inert for limit |
| A-RCB-07 | [02-capital-rcb-treasury.md](./02-capital-rcb-treasury.md) | If the owner does not ratify, Group A shall continue on the |
| A-RCB-08 | [02-capital-rcb-treasury.md](./02-capital-rcb-treasury.md) | The RCB service shall not pool Group A and Group B, and shall |
| A-REC-01 | [05-kernel-oms-reconciliation.md](./05-kernel-oms-reconciliation.md) | Reconciliation shall be event-driven and periodic: at least |
| A-REC-02 | [05-kernel-oms-reconciliation.md](./05-kernel-oms-reconciliation.md) | The broker is the source of truth; the fact log records the |
| A-REC-03 | [05-kernel-oms-reconciliation.md](./05-kernel-oms-reconciliation.md) | A discrepancy is a field-level difference between the |
| A-REC-04 | [05-kernel-oms-reconciliation.md](./05-kernel-oms-reconciliation.md) | Reconciliation may correct state projections; it cannot |
| A-SIG-01 | [04-strategy-quant-engine.md](./04-strategy-quant-engine.md) | A Kalman filter in tick mode shall emit a signal when its |
| A-SIG-02 | [04-strategy-quant-engine.md](./04-strategy-quant-engine.md) | A regime filter (GMM or HMM) shall condition signals. If |
| A-SIG-03 | [04-strategy-quant-engine.md](./04-strategy-quant-engine.md) | Black-Litterman shall combine the deterministic view with the |
| A-SIG-04 | [04-strategy-quant-engine.md](./04-strategy-quant-engine.md) | Advisory failure or abstention shall mean no advisory view |
| A-SIM-01 | [03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md) | 6 or more months of continuous SIM operation, with the SIM |
| A-SIM-02 | [03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md) | Clean reconciliation on at least 95% of sessions |
| A-SIM-03 | [03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md) | Net Sharpe of at least 1.2 after modelled trading costs |
| A-SIM-04 | [03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md) | Net monthly return of at least 6% sustained over at least 3 |
| A-SIM-05 | [03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md) | 200 or more trades, or a bootstrap confidence interval on |
| A-SIM-06 | [03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md) | No unresolved L2 or higher halt in the final 60 days |
| A-SIM-07 | [03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md) | A frozen strategy version: no parameter changes in the final |
| A-SIM-08 | [03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md) | The record survives Group A-scale sizing: intents are not |
| A-SWT-01 | [03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md) | LIVE to SIM shall be allowed at any time from the web app or |
| A-SWT-02 | [03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md) | On the switch the Group A LIVE account enters MANAGE_ONLY |
| A-SWT-03 | [03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md) | While Group A is LIVE, a SIM account can run the same intents |
| A-SWT-04 | [03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md) | Demo and paper fills are more optimistic than real fills. A |
| A-SZ-01 | [04-strategy-quant-engine.md](./04-strategy-quant-engine.md) | vol_scaled_risk shall reduce per-trade risk as realised |
| A-SZ-02 | [04-strategy-quant-engine.md](./04-strategy-quant-engine.md) | Sizes shall be rounded down to the lot step and never up. An |
| A-SZ-03 | [04-strategy-quant-engine.md](./04-strategy-quant-engine.md) | Fractional Kelly is retained only as an upper reference, not |
| A-SZ-04 | [04-strategy-quant-engine.md](./04-strategy-quant-engine.md) | Where the ramp factor applies it scales the limits defined by |
| A-TG-01 | [telegram-interface.md](./telegram-interface.md) | Every message shall start with a tag giving group, mode and |
| A-TG-02 | [telegram-interface.md](./telegram-interface.md) | Messages shall never contain credentials, keys or full |
| A-TG-03 | [telegram-interface.md](./telegram-interface.md) | The bot shall accept exactly one allowlisted chat and user |
| A-TG-04 | [telegram-interface.md](./telegram-interface.md) | Destructive commands shall require a confirm button within 30 |
| A-TG-05 | [telegram-interface.md](./telegram-interface.md) | Flood control shall deduplicate and coalesce bursts and cap |
| A-TG-06 | [telegram-interface.md](./telegram-interface.md) | Telegram shall expose no exposure-increasing action. Resume, |
| A-TRE-01 | [02-capital-rcb-treasury.md](./02-capital-rcb-treasury.md) | Every cost shall be tagged to A, B or GLOBAL (shared) |
| A-TRE-02 | [02-capital-rcb-treasury.md](./02-capital-rcb-treasury.md) | Own costs of Group A (broker fees, swaps, commissions, Group |
| A-TRE-03 | [02-capital-rcb-treasury.md](./02-capital-rcb-treasury.md) | The resulting lien is an obligation against future eligible |
| A-TRE-04 | [02-capital-rcb-treasury.md](./02-capital-rcb-treasury.md) | Group A's inability to reimburse its allocated costs shall |
| A-TRE-05 | [02-capital-rcb-treasury.md](./02-capital-rcb-treasury.md) | Infrastructure spend shall respect the Constitution's tier |
| A-TRE-06 | [02-capital-rcb-treasury.md](./02-capital-rcb-treasury.md) | The owner's temporary external funding of operating costs |
| A-UNI-01 | [04-strategy-quant-engine.md](./04-strategy-quant-engine.md) | The universe is G10 forex, gold and selected crypto CFDs; the |
| A-UNI-02 | [04-strategy-quant-engine.md](./04-strategy-quant-engine.md) | A Raw or zero-spread account with commission is preferred |
| A-UNI-03 | [04-strategy-quant-engine.md](./04-strategy-quant-engine.md) | No overnight directional bias by default |
