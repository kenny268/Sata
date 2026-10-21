//! Ordered verdict checks arrive in Phase 9. This crate is the boundary only.

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Decision {
    Allow,
    AllowWithSize,
    Reject,
    Throttle,
}
