# Group A — Decision Log

Track resolution of **IMPLEMENTATION BLOCKER — DECISION REQUIRED** items from Group A **§20** and Telegram open items (**OI-TG-***). Engineering shall not assume values marked open here.

**Source:** [`docs/source/SATE_Group_A_System_Documentation.docx`](../../source/SATE_Group_A_System_Documentation.docx) §20; [`docs/source/SATE_Telegram_Interface_Specification.docx`](../../source/SATE_Telegram_Interface_Specification.docx) §18.

Ambiguities and potential contradictions (undefined **N**, BF-06 vs A-EXE-03, etc.): [SOURCE-AMBIGUITIES.md](./SOURCE-AMBIGUITIES.md).

| ID | Decision | Status | Owner choice | Date | Blocks |
|----|----------|--------|--------------|------|--------|
| A-DEC-01 | Per-trade risk cap vs minimum lot at $500 floor (ramp interaction) | **OPEN** | — | — | LIVE gate, A-P0-21 |
| A-DEC-02 | LIVE-L2/L3 rungs, graduation, reverse-graduation params | **OPEN** | — | — | Rungs above L1 |
| A-DEC-03 | SIM-adequacy return hurdle (6% fixed vs cost-derived) | **OPEN** | — | — | Group A SIM gate |
| A-DEC-04 | Constitution tighten/loosen time-lock hours | **OPEN** | — | — | Final Constitution |
| A-DEC-05 | Shared-cost allocation when use is asymmetric | **OPEN** | Starting: pro-rata by RCB | — | Treasury |
| A-DEC-06 | End of temporary $60/mo funding bridge per group | **OPEN** | — | — | Treasury reporting |
| A-DEC-07 | Windows host: VPS vs owned PC vs broker VPS | **OPEN** | — | — | Impl. phases **11**, **19** |
| A-DEC-08 | Emergency relay endpoint, auth, replay policy | **OPEN** | — | — | Production control |
| A-DEC-09 | Numeric RPO and RTO targets | **OPEN** | — | — | LIVE gate |
| A-DEC-10 | Kenya broker/tax verification (Exness) | **OPEN** | — | — | LIVE |
| OI-TG-01 | SIM→LIVE code via Telegram, enter in web | **OPEN** | Spec assumes yes | — | Mode arming UX |
| OI-TG-02 | Away-mode maximum duration | **OPEN** | Constitution max 30d under review | — | Check-in |
| OI-TG-03 | Emergency relay (links A-DEC-08) | **OPEN** | — | — | Control plane |
| OI-TG-04 | Limited control token as distinct crypto authority | **OPEN** | — | — | Security model |
| OI-TG-05 | INFO/NOTICE batching thresholds | **OPEN** | — | — | TG-13 |
| OI-TG-06 | Floor warning severity WARN | **CONFIRMED** | Matches group docs | 2026-10-16 | — |

**Status values:** OPEN | DECIDED | DEFERRED (with LIVE impact noted)

When a row moves to **DECIDED**, record the chosen values in the Group A Constitution artifact (Appendix A fields) and a fact-log configuration event.
