//! Exness trade credentials exist only in this crate (A-KRN-02, A-PR-02).
//! The sealed file is encrypted. Startup injects it once, then wipes it.
//! A SIM kernel refuses a LIVE record. Host-path separation remains Phase 19.

mod aead;
mod vault;

pub use vault::{inject_at_startup, rotate_text, seal_text, Audit, Material, VaultError};
