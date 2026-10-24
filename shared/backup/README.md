# Backup

Encrypted fact-log snapshots, restore-with-verify drill, **A-LOG-04** gzip cold archive + manifest, backup job success/failure metrics, monthly drill orchestrator, and **A-DEC-09** RPO/RTO register validation. Set `SATE_BACKUP_KEY` (Fernet key) at deploy time; never commit keys.

Deploy: `python -m sate_backup.bootstrap` (compose service `backup`). Scheduled copies: `python -m sate_backup.runner` with `SATE_FACTLOG_DB`, `SATE_BACKUP_KEY`, optional `SATE_BACKUP_DIR` and `SATE_BACKUP_REMOTE_DIR`.
