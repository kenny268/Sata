# Notifier bot

Reduce-only Telegram control plane (**Phase 18**). Allowlist, replay, and fact-log logging are on. Destructive buttons are signed only when `SATE_NOTIFIER_CONFIRM_SECRET` is set; an empty secret does not confirm. INFO/NOTICE batching stays unset until the owner sets the **OI-TG-05** cap, and a LIVE desk does not invent one. The long-poll runner (`python -m sate_notifier.runner`) also needs `SATE_TELEGRAM_BOT_TOKEN`, `SATE_TELEGRAM_CHAT_ID`, and `SATE_TELEGRAM_USER_ID`. Compose runs `python -m sate_notifier.bootstrap`. No bot token is stored in the repo.
