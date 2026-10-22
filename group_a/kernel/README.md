# KERNEL-A

Rust workspace. Crates are split so strategy code cannot link the credential vault.

| Crate | Behaviour |
|-------|-----------|
| `credentials` | Sealed vault. Startup inject only. SIM refuses LIVE. |
| `verdict` | Ordered checks, halt file, mock adapter. |
| `oms` | One order per intent. Timeout waits for a broker query. |
| `reconcile` | Five-second compare with broker truth. A mismatch is an immediate L2. |
| `constitution` | Verifies the pinned signed constitution. |
| `kernel-a` | Refuses to start without a signed release and constitution. |

```bash
cargo test --workspace
```

Run from this directory. No broker connection.

Rotation stays inside this crate. Write a new 32-byte key outside the repo, re-seal the vault with `rotate_text`, and record the fact-log action `rotate` with the credential id and the key ids. The login, password, and server are not in that record. After kill state K3 the vault stays sealed. The control API, notifier, web, strategy, and MT5 bridge cannot name this crate. Separate SIM and LIVE host paths remain Phase 19. The kernel process is still not in the compose file.
