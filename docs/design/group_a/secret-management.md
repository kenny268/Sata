# Secret management (Phase 1 design)

No secret values belong in this repository.

| Secret class | Where it may exist at runtime | Where it must not exist |
|--------------|-------------------------------|-------------------------|
| Exness trade credentials | `group_a/kernel/credentials/` process memory and a kernel-only vault (Phase 10) | `shared/`, `group_a/strategy/`, `group_a/broker/mt5-bridge/`, git, CI logs |
| Group B broker credentials | `group_b/kernel/credentials/` when that kernel exists | Group A tree, shared services |
| Telegram bot token and limited control token | `shared/notifier-bot/` runtime environment | Kernel, strategy, git |
| WebAuthn / session material | `shared/control-api/` runtime | Fact log payloads, Telegram messages |
| Backup encryption keys | `shared/backup/` runtime | Git |

CI injects nothing in Phase 1. Workflows build stubs only. Environment names are `dev`, `staging` (SIM), `pre-live`, and `production`. Production stays incapable of LIVE trading until the §19 preflight in later phases passes. See `group_a/infra/README.md`.
