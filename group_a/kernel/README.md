# KERNEL-A

Rust workspace. Crates are split so strategy code cannot link the credential vault.

| Crate | Phase 1 behaviour |
|-------|-------------------|
| `credentials` | Boundary only. Stores nothing. |
| `verdict` | Decision enum only. |
| `oms` | Empty library. |
| `reconcile` | Empty library. |
| `constitution` | Empty library. |
| `kernel-a` | Binary that prints a stub line and exits. |

```bash
cargo test --workspace
```

Run from this directory. No broker connection.
