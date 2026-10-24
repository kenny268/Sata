# Email notifier

Owner check-in reminders (**Phase 16**, **A-CHK-03**). Set `SATE_EMAIL_TRANSPORT=console` for CI/SIM or `smtp` with `SATE_SMTP_HOST`, `SATE_SMTP_PORT`, `SATE_SMTP_USER`, `SATE_SMTP_PASSWORD`, and `SATE_SMTP_FROM` for production (**Appendix D** assumption **APP-D-EMAIL-01**). OPS drills **OP-01**–**OP-06** and runbook **C.6** live in `sate_email.ops_drill` and `sate_email.c6_runbook`.
