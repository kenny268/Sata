# Group A infrastructure

Phase 1 defines the A-only control-plane network. It does not provision a Windows host. **A-DEC-07** (VPS vs owned PC vs broker VPS) stays open, so KERNEL-A and MT5 are absent from this compose file.

| Tier | Role |
|------|------|
| `dev` | `docker compose -f group_a/infra/compose.yaml config` and a local stub run. No broker. |
| `staging` | Future SIM account. Demo credentials only, inside the kernel vault. |
| `pre-live` | Production-like controls. LIVE arming disabled. |
| `production` | LIVE-capable only after the §19 preflight. Not enabled in Phase 1. |

The compose file is [compose.yaml](./compose.yaml): fact log, control-api, notifier-bot, and monitoring on network `sate-a-control`. Images are read-only placeholders. No ports, volumes, or credentials.

Deploy artifacts are named `group-a-<git-sha>` and are not retagged. On a push to `main` that changes `group_a/`, CI also creates the git tag `group-a-<git-sha>`.
