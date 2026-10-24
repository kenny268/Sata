# Notifier bot

Reduce-only Telegram control plane (**Phase 18**). Delivers **TG-PO-01–15**: allowlist/replay/logging, signed confirms, scope flows, `/alive`, away→web, control-api integration, fact-log subscription, **`/why`** (fact-sourced), **`/digest`**, **`/mute`** (CRITICAL bypass), treasury/health templates, and optional **`SATE_TELEGRAM_BOT_TOKEN`** long-poll runner (`python -m sate_notifier.runner`).

Compose runs `python -m sate_notifier.bootstrap`. No bot token is stored in the repo.
