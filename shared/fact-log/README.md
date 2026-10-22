# Fact log

Append-only hash chain for control and capital events. Each row stores a CRC32 of its payload and the SHA-256 of the previous row. Corrections are new events. Updates and deletes are rejected by the database.

Writers and readers must be on the allowlist (`identity`, `kernel-a`, `control-api`, `capital`, `rcb` in staging). An unknown writer cannot append, and an unknown reader cannot poll, query, export, or verify. A failed write raises `FactLogWriteError` and does not return an event. Halt, capital state, owner action, constitution, failure, and state-transition failures use policy `BLOCK`. Other types use `DEGRADE`.

A correction is a new event with `corrects_event_id`. The original row stays as it was. There is no method that increases RCB. An `rcb_change` row records a fact; cool-off and ratification belong to the capital service.

Group A identity polls with `poll(after_seq, group_scope="A", reader_id="identity")` and applies those records. The identity service opens the log read-only. A transition stored under another scope is not applied to the Group A identity store. Events that share a `correlation_id` can be read back for one scope.

Staging bootstrap records the soak start time on first run and does not move it later. `soak_status` reports elapsed days. A new database has `gate_met` false. This package does not treat that gate as passed.

Staging config: `config/staging.json`. Local database path `var/` is gitignored.
