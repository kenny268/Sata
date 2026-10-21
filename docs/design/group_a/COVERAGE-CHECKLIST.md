# Group A design — source coverage checklist

Maps **Group A System Documentation** (§1–20, Appendices A–D) and **Telegram Interface Specification** (§0–18) to design documents in this folder. Status: **Covered** | **Partial** | **Blocked** (owner decision).

**Legend:** GA = Group A source doc; TG = Telegram spec.

| Source | Design document(s) | Status |
|--------|-------------------|--------|
| GA §1 Introduction, independence, terminology | [01-system-overview-independence.md](./01-system-overview-independence.md) | Covered |
| GA §2 Overview, principles, actors, shared services | [01-system-overview-independence.md](./01-system-overview-independence.md), [architecture-components.md](./architecture-components.md) | Covered |
| GA §3 Capital and accounting | [02-capital-rcb-treasury.md](./02-capital-rcb-treasury.md) | Covered |
| GA §4 Modes, SIM→LIVE, ladder, SIM-adequacy | [03-modes-ladder-sim-gates.md](./03-modes-ladder-sim-gates.md) | Partial (A-DEC-01–03, A-DEC-02) |
| GA §5 Strategy and quant engine | [04-strategy-quant-engine.md](./04-strategy-quant-engine.md) | Partial (A-COG-04 gate TBD) |
| GA §6 Kernel, OMS, reconciliation, failures | [05-kernel-oms-reconciliation.md](./05-kernel-oms-reconciliation.md) | Covered |
| GA §7 Broker / Exness MT5 | [06-broker-exness-mt5.md](./06-broker-exness-mt5.md) | Partial (§7.4 verification) |
| GA §8 Constitution, deploy, crypto | [07-constitution-crypto-deployment.md](./07-constitution-crypto-deployment.md) | Partial (A-DEC-04) |
| GA §9 Halts, kill, check-in | [08-halts-kill-checkin.md](./08-halts-kill-checkin.md) | Covered |
| GA §10 Treasury | [02-capital-rcb-treasury.md](./02-capital-rcb-treasury.md) | Partial (A-DEC-05, A-DEC-06) |
| GA §11 Cognitive plane | [09-cognitive-plane.md](./09-cognitive-plane.md) | Partial (**CG-LIVE** / A-COG-04 threshold undefined) |
| GA §12 Data, fact log, journal, retention | [10-data-audit-fact-log.md](./10-data-audit-fact-log.md) | Covered |
| GA §13 Web + Telegram summary | [11-web-control-api.md](./11-web-control-api.md), [telegram-interface.md](./telegram-interface.md) | Covered |
| GA §14 Monitoring, backup | [12-monitoring-backup-continuity.md](./12-monitoring-backup-continuity.md) | Partial (A-DEC-09) |
| GA §15 Operational scenarios | [13-scenarios-runbooks.md](./13-scenarios-runbooks.md) | Covered |
| GA §16 Verification, invariants | [14-verification-risks-live-gates.md](./14-verification-risks-live-gates.md) | Covered |
| GA §17 Risks and design review | [14-verification-risks-live-gates.md](./14-verification-risks-live-gates.md) | Covered |
| GA §18 Implementation plan | [implementation-phases.md](./implementation-phases.md), [traceability-matrix.md](./traceability-matrix.md) | Covered |
| GA §19 DoD and LIVE gates | [14-verification-risks-live-gates.md](./14-verification-risks-live-gates.md) | Covered |
| GA §20 Decisions | [decision-log.md](./decision-log.md) | Blocked items tracked |
| GA Appendix A Constitution example | [15-persistent-schemas-constitution.md](./15-persistent-schemas-constitution.md) | Covered |
| GA Appendix B Entities/schemas | [15-persistent-schemas-constitution.md](./15-persistent-schemas-constitution.md) | Covered |
| GA Appendix C Runbooks | [13-scenarios-runbooks.md](./13-scenarios-runbooks.md) | Covered |
| GA Appendix D Assumptions | [14-verification-risks-live-gates.md](./14-verification-risks-live-gates.md), [decision-log.md](./decision-log.md) | Partial |
| TG §0–18 Full Telegram spec | [telegram-interface.md](./telegram-interface.md) | Covered |
| Deployment (A-only) | [independent-deployment-strategy.md](./independent-deployment-strategy.md) | Covered |
| Repository layout, SoC, CI path filters | [repository-layout.md](./repository-layout.md) | Covered |

## Requirement ID inventory (132 `A-*` IDs in GA source)

Every ID is listed in [requirements-index.md](./requirements-index.md) with primary design doc link. [traceability-matrix.md](./traceability-matrix.md) adds phase mapping, backlog, scenarios, and verification classes at family level. Engineering shall not implement behaviour for an ID without a design section reference or an explicit **BLOCKED** entry in [decision-log.md](./decision-log.md).

## Telegram families

| Family | Count (source) | Design home |
|--------|----------------|-------------|
| TG-01–TG-16 | 16 | [telegram-interface.md](./telegram-interface.md) §Requirements |
| TG-S-01–TG-S-25 | 25 | [telegram-interface.md](./telegram-interface.md) §Scenarios |
| TG-T-01–TG-T-15 | 15 | [telegram-interface.md](./telegram-interface.md) §Tests |
| TG-PO-01–TG-PO-15 | 15 | [telegram-interface.md](./telegram-interface.md) §Backlog |
| SEC-01–SEC-07 | 7 | [telegram-interface.md](./telegram-interface.md) §Security |

## Known ambiguities / contradictions (do not resolve silently)

Documented in [SOURCE-AMBIGUITIES.md](./SOURCE-AMBIGUITIES.md).
