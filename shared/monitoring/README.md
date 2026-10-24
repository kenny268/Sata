# Monitoring

Phase 19 observability: SLO snapshots, on-call routing (CRITICAL → all channels), structured trace records, Appendix D market-data/news licence hooks, **TG-PO-15** wire, kernel heartbeat stall alerts (≤60s budget), MT5 bridge observations (HEALTHY/DEGRADED mapping), fact-log chain CRITICAL path (**A-P0-17**), and runbook **C.2** + ops drill.

Deploy: `python -m sate_monitoring.bootstrap` (compose service `monitoring`). No secrets in repo.
