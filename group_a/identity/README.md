# Group A identity

Account registry for **A-SIM** and **A-LIVE** (**A-P0-01**). The SQLite file is the isolated Group A store (**A-P0-03**). It accepts `group_id = A` only. Fingerprint history is append-only. Risk projections require `account_mode` and reject pooled capital fields (**A-MOD-03**, **INV-03**).

Default scope is **A**. Staging configuration: [config/staging.json](./config/staging.json). The database path in that file is created at deploy time and is not committed.

```bash
PYTHONPATH=group_a/identity python -m unittest discover -s group_a/identity/tests -t group_a/identity
```

Fact-log hash chaining is Phase 3. `project_risk` is the frozen projection contract those events will feed.
