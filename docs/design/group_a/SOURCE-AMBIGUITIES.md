# Source material — ambiguities and contradictions

Items flagged during design expansion. **Engineering shall not pick a silent default** where the Group A source marks **IMPLEMENTATION BLOCKER — DECISION REQUIRED** (§20).

## Open decisions (Group A §20)

See [decision-log.md](./decision-log.md) for **A-DEC-01** through **A-DEC-10**.

## Telegram open items (TG spec §18)

See [decision-log.md](./decision-log.md) for **OI-TG-01** through **OI-TG-06**.

## Undefined parameters in otherwise binding requirements

| Location | Issue | Design treatment |
|----------|--------|------------------|
| **A-SIG-02** | Regime filter disabled when output is “unstable for **N** sessions”; **N** not specified | Implement as Constitution-configurable `regime_instability_sessions`; default unset → **BLOCKED** until owner sets starting value |
| **A-LAD-05** | Ramp drawdown return-to-SIM threshold: “starting proposal **20%**” | Treat as Constitution field `ramp_max_drawdown_pct`; confirm in **A-DEC-02** alongside L2/L3 |
| **A-KIL-03** | Resume cool-off “example **15 minutes**” | Constitution field `resume_cooloff_minutes`; not hard-coded without owner ratification |
| **TG-13 / OI-TG-05** | INFO/NOTICE batching volume threshold and `no_batch` message list | Rate limiter configurable; LIVE behaviour blocked until threshold decided |
| **Appendix A** | `tighten_lock_hours = 0`, `loosen_lock_hours = 0` placeholders | **A-DEC-04** |

## Potential overlap / clarify with owner (not necessarily contradictory)

| Topic | Observation |
|-------|-------------|
| **Reverse graduation params** | **A-LAD-01–03** already specify 10% warning band, 3 sessions, 14-day re-entry. **A-DEC-02** asks to “confirm reverse-graduation parameters” for L2/L3 — may mean **confirm for higher rungs only** or re-confirm global ladder. Design keeps L1 rules as §4.5; L2/L3 graduation remains **BLOCKED** on A-DEC-02. |
| **A-TG-* vs TG-*** | Group A §13.4 lists **A-TG-01–06**; Telegram spec lists **TG-01–16** and **SEC-01–07**. Both apply; implementation must satisfy the **stricter union**. |
| **SIM-to-LIVE code** | Group A §4.3 step 4 and TG spec callout + **TG-16** / **OI-TG-01**: code via Telegram, entry in web only. Aligned; OI-TG-01 still formally OPEN in decision log. |
| **BF-06 server-side stop** | Group A §15.7 BF-06 allows “monitored server-side stop **where the frozen design allows**” vs **A-EXE-03** broker-side stop on every entry. **Primary:** broker-side stop required; server-side is **fallback only** if broker verification (§7.4) documents unsupported case — must not replace broker stop without owner decision. |
| **$1,500 combined reference** | §3.3 planning reference vs **A-DEC-06** bridge end — must never gate per-group eligibility (**INV-03**). |

## Broker and tax (verification blockers)

§7.4 and **A-DEC-10**: No LIVE capability enabled until written verification for Kenya-resident Exness account type, products, leverage, withdrawals, protective orders, and tax/reporting treatment.

## Recovery objectives

**A-DEC-09**: Harness and evidence schema may be built; **LIVE gate blocked** until numeric RPO/RTO set (GA §14.2).

## Cognitive plane live gate

**A-COG-04**: “Phase 6 gate” in source = **CG-LIVE** (not implementation Phase 6). **Methodology and pass threshold not defined**. Design: shadow in **Phase 21**; owner criteria in **Phase 25**; LIVE may run with advisory = 0 (**A-COG-01**).
