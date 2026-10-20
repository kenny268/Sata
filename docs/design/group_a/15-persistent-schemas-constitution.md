# Persistent entities, execution schemas, and Constitution example

**Source:** Group A Appendix A, Appendix B.

---

## 1. Entity catalogue (Appendix B)

All trading entities carry **`group_id = A`** unless genuinely GLOBAL infrastructure metadata.

| Entity | Key fields (design) |
|--------|---------------------|
| **AccountProfile** | `account_id`, `group_id=A`, `broker_id`, `environment`, `fingerprint`, `account_type`, `currency`, `verified_at`, `verification_status` |
| **CapitalSnapshot** | `snapshot_id`, `group_id`, equity, realised_pnl, settled/reserved/withdrawable cash, `source_ts`, `recorded_at` |
| **RCBState** | `group_id`, `ratified_base`, `effective_rcb_equity`, `rcb_realised`, state, `clean_period_start`, `ratified_at` |
| **Constitution** | `constitution_id`, `group_id`, version, `effective_at`, `payload_hash`, signature, `key_id`, status |
| **Intent** | `intent_id`, `group_id`, `strategy_id`, `model_version`, instrument, side, quantity, `risk_inputs`, `provenance_refs` |
| **Verdict** | `verdict_id`, `intent_id`, `group_id`, result, `approved_size`, checks[], constitution/kernel version, latency |
| **Order** | `order_id`, `client_id`, `group_id`, `broker_order_id`, status, qty fields |
| **Fill** | `fill_id`, `order_id`, `group_id`, `broker_fill_id`, qty, price, fees, currency, `broker_ts` |
| **Position** | `position_id`, `group_id`, instrument, quantity, `avg_price`, `protective_stop_ref`, `broker_ts` |
| **TreasuryObligation** | `obligation_id`, `group_id`, amount, currency, `due_at`, broker dependency, reserve flag, status |
| **Reimbursement** | `reimbursement_id`, `group_id`, `owner_cost_id`, amount, currency, auth/confirm/reconcile timestamps, status |
| **HaltCommand** | `command_id`, scope, issuer, `requested_at`, `ack_A`, `ack_B`, external emergency state, `final_state` |
| **OwnerAction** | `action_id`, actor, `auth_method`, scope, command, confirmation, timestamp |

---

## 2. ExecutionIntent (Appendix B)

```
intent_id, trace_id, group (A), account_mode (SIM|LIVE),
instrument, side, quantity, order_type, limit_price?,
protective_stop?, take_profit?, slippage_budget,
strategy_id, signal_refs[], advisory_refs[], created_at
```

Validation: JSON/schema before kernel IPC; kernel re-validates universe and mode.

---

## 3. Verdict (Appendix B)

```
intent_id, kernel_version, constitution_version,
decision: Allow | AllowWithSize(q) | Reject(reason) | Throttle,
checks[] { name, passed, value, limit },
halt_level, kill_state, latency_us, issued_at
```

Persist every verdict to fact log before OMS submit (**INV-01**).

---

## 4. Constitution example structure (Appendix A)

Placeholder values — owner sets production values; open decisions marked.

```toml
[meta]
constitution_id = "A-001"
group = "A"
version = 1
signed_by = "owner-key-1"
tighten_lock_hours = 0   # A-DEC-04 placeholder
loosen_lock_hours = 0    # A-DEC-04 placeholder

[mode]
state = "SIM"            # SIM | LIVE-L1 | LIVE-L2 | LIVE-L3
arming_delay_hours = 24
ramp_factor = 0.25
ramp_min_days = 30
evidence_window_days = 90

[universe]
LIVE-L1 = ["EURUSD"]
LIVE-L2 = []             # A-DEC-02

[risk]
max_risk_per_trade_pct = 0.5      # A-DEC-01
max_open_notional_x_equity = 3.0
max_daily_loss_pct = 2.0
max_drawdown_pct = 10.0
max_leverage_used = 10
require_protective_stop = true
broker_balance_cap = 0            # 0 blocks LIVE until owner sets

[capital]
reference_floor = 500
floor_warning_band_pct = 10
floor_breach_sessions = 3
reentry_block_days = 14
ratified_base = 0
ratify_cooloff_days = 14
ratify_requires = ["web_passkey"]
pause_injections_on = "L2+"

[checkin]
reminder_days = 7
manage_only_days = 10
flatten_days = 14
max_away_days = 30

[treasury]
cash_floor = 0
cost_allocation = "pro_rata_rcb"  # A-DEC-05
obligations_file = "obligations_A.toml"

[notifications]
quiet_hours_utc = "20:00-04:00"
mask_amounts = false
```

Kernel refuses load if signature/version/key/effective window invalid (**A-CON-01**).

---

## 5. Database design notes

- Separate **projection tables** from fact log; projections rebuildable from chain.
- Index: `(group_id, account_mode, occurred_at)` for reporting.
- No column `total_equity_ab` used by kernel services (**INV-03**).
- Migration policy: additive; compensating events for corrections not UPDATE on fact rows.
