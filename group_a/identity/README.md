# Group A identity

Account registry for **A-SIM** and **A-LIVE** (**A-P0-01**). The SQLite file is the isolated Group A store (**A-P0-03**). It accepts `group_id = A` only. Fingerprint history is append-only. Risk projections require `account_mode` and reject pooled capital fields (**A-MOD-03**, **INV-03**).

Default scope is **A** for every control-plane service. Staging configuration: [config/staging.json](./config/staging.json). `python -m sate_identity.bootstrap` creates that database from `SATE_GROUP_SCOPE` and `SATE_IDENTITY_DB`. The compose file runs this once on the `sate-a-identity` volume.

```bash
PYTHONPATH=group_a/identity python -m unittest discover -s group_a/identity/tests -t group_a/identity
```

`consume_fact_event` reads a fact-log envelope and writes a Group A risk projection. Hash chaining is Phase 3. Envelopes for any other scope are rejected and leave the store unchanged.
