# Windows execution host (A-DEC-07)

Group A **KERNEL-A** and **MT5** terminals run on a dedicated Windows host. The Linux control plane in `compose.yaml` does not host the kernel or broker terminals.

## Recorded decision

- **A-DEC-07:** Windows host is the approved execution surface for MT5 and KERNEL-A.
- Restarts and OS updates are scheduled **outside** trading windows.
- On restart, the kernel reloads halt state from disk and reconciles with the broker before any risk-increasing resume.

## Network policy (summary)

- Control plane services use the internal `sate-a-control` bridge only; **no published ports** in compose.
- The Windows host reaches control-api and fact log over operator-configured private paths (VPN or tailnet); credentials are not stored in this repository.
- MT5 bridge emits adapter state and poll failures to monitoring (`shared/monitoring/sate_monitoring/bridge.py`).

See [independent-deployment-strategy.md](../../docs/design/group_a/independent-deployment-strategy.md) and [06-broker-exness-mt5.md](../../docs/design/group_a/06-broker-exness-mt5.md).
