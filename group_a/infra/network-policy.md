# Group A network policy (Phase 19)

Aligned with [independent-deployment-strategy.md](../../docs/design/group_a/independent-deployment-strategy.md).

## Control plane (Linux / compose)

- Services attach only to `sate-a-control`; **no published host ports** in `compose.yaml`.
- Inter-service traffic stays on the bridge; secrets via `SATE_*` env at deploy time only.

## Windows execution host (A-DEC-07)

- KERNEL-A and MT5 terminal reach control-api and fact log over a **private path** (VPN, tailnet, or site-to-site).
- Broker credentials live on the Windows host under `group_a/kernel/credentials/` (never in git).
- Inbound to the Windows host is limited to operator admin and required broker/market-data endpoints.

## Backup and monitoring

- Encrypted backups copy to `SATE_BACKUP_REMOTE_DIR` when set (`sate_backup.runner`).
- External metrics scrapers pull Prometheus text from the monitoring export helper at deploy time (no scrape port in compose by default).

## Verification

- Run `shared/ci/windows-host-checklist.json` before claiming production Windows provisioning.
