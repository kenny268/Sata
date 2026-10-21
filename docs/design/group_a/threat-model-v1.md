# Threat model v1 (Phase 1)

Seed for Group A **§17** and Phase 1 exit. This is a risk register, not an attack procedure. Controls are the ones already required by the system documentation.

| ID | Threat | Impact | Phase 1 control | Later enforcement |
|----|--------|--------|-----------------|-------------------|
| TM-01 | Kernel trade-credential theft | Attacker places broker orders | Credentials crate exists only under `group_a/kernel/credentials/`. No secrets in git (`.gitignore`). Strategy and `shared/` must not depend on that crate | **A-KRN-02**, **A-PR-02**, Phases 9–10 |
| TM-02 | Telegram reduce-only bypass | Bot resumes trading or arms LIVE | `notifier-bot` is a stub with no command handlers. Workflow does not ship a bot token | **TG-09**, **A-KIL-02**, Phase 18 |
| TM-03 | Cross-group scope confusion | Group B capital or commands affect Group A | `require_scope` accepts only `A` or `B`. Repo test forbids `group_a` importing `group_b` | **A-IND-02**, **A-IND-03**, **INV-03**, Phase 2+ |
| TM-04 | Fact-log tampering | Audit trail rewritten | `shared/fact-log/` is a stub with no writer that skips the chain. No production log store yet | **A-LOG-05**, Phase 3 |

Assumption register (**§17.1** item 6): undefined parameters stay in [SOURCE-AMBIGUITIES.md](./SOURCE-AMBIGUITIES.md) and [decision-log.md](./decision-log.md).  
Group B absent (**§17.1** item 7): `group_b/` is a placeholder; halt design still forbids inferring `HALT_CONFIRMED_ALL` from an unreachable B kernel ([independent-deployment-strategy.md](./independent-deployment-strategy.md)).
