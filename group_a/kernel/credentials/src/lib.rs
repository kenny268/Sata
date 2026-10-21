//! Exness trade credentials may exist only in this crate (A-KRN-02, A-PR-02).
//! Phase 1 keeps the boundary and stores no secrets.

/// Marker for the credential boundary. Later phases load a vault here.
pub struct CredentialVault;

impl CredentialVault {
    pub const PHASE: &str = "1-stub";
}

#[cfg(test)]
mod tests {
    use super::CredentialVault;

    #[test]
    fn phase_one_holds_no_secret_material() {
        assert_eq!(CredentialVault::PHASE, "1-stub");
    }
}
