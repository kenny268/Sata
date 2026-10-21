# ADR-0001 — Repository layout and independent deploy

**Status:** Accepted (Phase 1 engineering scaffold)  
**Date:** 2026-10-21  
**Deciders:** Owner direction recorded in design review; engineering implements [repository-layout.md](../repository-layout.md)

## Context

Group A must run as a complete domain while Group B is absent (**A-IND-04**). A change that only affects Group B must not rebuild or restart Group A. Trade credentials must stay inside each group's kernel (**A-PR-02**, **A-KRN-02**). Combined figures are reporting-only (**INV-03**).

Open product decisions (**A-DEC-01–10**, **OI-TG-01–06**) stay **OPEN** in [decision-log.md](../decision-log.md). This ADR does not choose those values.

## Decision

1. One git repository with three code roots: `group_a/`, `group_b/`, `shared/`.
2. `group_a/` and `group_b/` do not import each other.
3. Shared services (fact log, capital/RCB/treasury APIs, halt coordinator, control-api, web, notifier-bot, market data, monitoring, backup, signed kill CLI) live under `shared/` and require an explicit group scope.
4. CI workflows `deploy-group-a`, `deploy-group-b`, and `deploy-shared` use path filters. A `group_b/**`-only change does not run the Group A deploy workflow.
5. Runtime topology for the first delivery remains **A-only** as in [independent-deployment-strategy.md](../independent-deployment-strategy.md). Group B source may exist as a placeholder without a running kernel.

## Consequences

- Phase 1 scaffolds stubs and workflows only. Trading behaviour starts in later phases.
- A breaking change under `shared/schemas/` ships with the shared artifact. Group kernels adopt it on their next group deploy unless a later ADR requires a coordinated restart.
- Hosting choice (**A-DEC-07**) remains open; `group_a/infra/` documents tiers without selecting a Windows vendor.
