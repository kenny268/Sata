# Strategy and quantitative engine

**Source:** Group A §5; scenarios §15.1 (TS-*), §15.8 (MP-*); **A-UNI-***, **A-SIG-***, **A-SZ-***, **A-EXE-***, **A-PERF-***.

---

## 1. Universe (§5.1)

| ID | Rule |
|----|------|
| **A-UNI-01** | G10 FX, gold, selected crypto CFDs; Constitution + **current rung**; **LIVE-L1: EUR/USD only** (starting) |
| **A-UNI-02** | Prefer raw/zero-spread + commission vs wide spread standard |
| **A-UNI-03** | No overnight directional bias by default |

Constitution example: `[universe] LIVE-L1 = ["EURUSD"]`; LIVE-L2 empty until **A-DEC-02**.

---

## 2. Signal pipeline (§5.2, §6.1)

```
MT5 ticks + calendar
  → freshness validation
  → Kalman (tick mode, innovation threshold)
  → regime (GMM/HMM) — optional tilt
  → AdvisorySignal (optional, signed)
  → Black-Litterman blend
  → sizing → Intent
  → pre-kernel validation
  → KERNEL-A
```

| ID | Rule |
|----|------|
| **A-SIG-01** | Kalman signal when innovation > threshold (**2.5σ** starting); frozen last 3 months of SIM evidence |
| **A-SIG-02** | Regime conditions signals; if unstable **N sessions** → disable tilt ( **N** undefined — see [SOURCE-AMBIGUITIES.md](./SOURCE-AMBIGUITIES.md) ) |
| **A-SIG-03** | Black–Litterman combines deterministic + advisory; single instrument → Kalman + advisory (LIVE-L1 expected) |
| **A-SIG-04** | Advisory failure/abstention → no advisory view |

Advisory integration: [09-cognitive-plane.md](./09-cognitive-plane.md).

---

## 3. Position sizing (§5.3)

**Formulas (deterministic):**

```
capital_base = min(ratified_capital_base_A, broker_equity_A)

risk_budget = min(max_risk_per_trade_pct, vol_scaled_risk) * capital_base * ramp_factor

stop_distance = k_stop * ATR(instrument)

size_raw = risk_budget / (stop_distance * value_per_unit)

size = floor_to_lot_step(min(size_raw, notional_cap_size, leverage_cap_size))

if size < min_lot OR size * stop_distance * value_per_unit > risk_budget:
  REJECT (untradeable_at_this_capital)
```

| ID | Rule |
|----|------|
| **A-SZ-01** | `vol_scaled_risk` reduces per-trade risk when vol rises |
| **A-SZ-02** | Round **down** to lot step; min lot > budget → reject + log |
| **A-SZ-03** | Fractional Kelly = upper reference only, not sizing method |
| **A-SZ-04** | Ramp factor scales limits; interaction with min lot → **A-DEC-01** |

Kernel re-validates per-trade budget at check **#6** (§6.4).

---

## 4. Costs, execution, protection (§5.4)

| ID | Rule |
|----|------|
| **A-EXE-01** | Model spread, commission, swap (incl. Wed triple), slippage |
| **A-EXE-02** | Swap-cost guard + news blackout; calendar reload at FX week open (Sun 17:00 NY) |
| **A-EXE-03** | Every entry: **broker-side protective stop**; cannot place → do not open |
| **A-EXE-04** | Slippage budget breach on rolling **20-trade** window → **L1** halt behaviour |

**Starting slippage budgets** (replace with measured SIM/LIVE):

| Class | Budget |
|-------|--------|
| EUR/USD | 0.5 pip |
| GBP/JPY | 2.0 pips |
| Gold | 20 cents |
| Bitcoin CFD | $50 |

---

## 5. Methods and research modules (§5.5)

| Function | Method |
|----------|--------|
| Trend | Kalman tick mode, innovation-covariance breaks |
| Blending | Black–Litterman |
| Regime | GMM/HMM, online EM, forgetting factor |
| Research modules | Triangular arb graph, wavelet/FFT cycles, RL execution — **each gated before live** |
| Backtest | Vectorised full cost model; **no LLM in backtest loop** |

**A-P2-01:** Later modules / wider universe at higher rungs — nothing live without gate.

---

## 6. Performance and retirement (§5.5)

| ID | Rule |
|----|------|
| **A-PERF-01** | Success = net-of-all-costs vs passive benchmark (cash/T-bills); **time-weighted** returns (funding events excluded) |
| **A-PERF-02** | Retirement: when min sample met, block bootstrap (10k, 95%) lower bound on net excess return ≤ 0 → retire to cash |

---

## 7. Model promotion (§15.8)

- One-sided **95%** block-bootstrap on daily net excess return diff (challenger − champion) > 0.
- Floor: **≥8 weeks**, **≥100** independent shadow decisions (starting values).
- No-worse: drawdown, cost, veto rate, calibration.
- Probation: **~20 trading days**; champion stays in shadow.
- Promotion **never** loosens kernel limits or Constitution.
- Kalman threshold tuning = challenger; **frozen** last 3 months SIM; trained on market/outcomes, **not** champion decisions.

Scenarios: MP-01–MP-03 in [13-scenarios-runbooks.md](./13-scenarios-runbooks.md).

---

## 8. Trading scenarios (§15.1) — behaviour contract

| ID | Expected system behaviour (abbrev.) |
|----|-------------------------------------|
| **TS-01** | Valid signal → blend → size → intent → kernel Allow → order + stop + journal before act |
| **TS-02** | Cognitive down → zero advisory; Kalman continues |
| **TS-03** | ABSTAIN + digest; zero view |
| **TS-04** | Reject `untradeable_at_this_capital` |
| **TS-05** | Kernel Reject with reason + limit values |
| **TS-06** | AllowWithSize |
| **TS-07** | Throttle |
| **TS-08** | Blackout reject |
| **TS-09** | Swap guard reject/exit rule |
| **TS-10** | Stale data → no new risk; L1/L2 by severity |
| **TS-11** | Idempotent duplicate / reconcile-before-retry |
| **TS-12** | Partial fill lifecycle; stop matches filled qty |
| **TS-13** | No open without stop |

Telegram: TRADE / ABSTAIN / ERROR categories — [telegram-interface.md](./telegram-interface.md).
