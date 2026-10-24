//! Owner kill switch **K1–K3** (**A-KIL-01**, **A-P0-14**).

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum KillError {
    Unknown,
    Sealed,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum KillLevel {
    K1,
    K2,
    K3,
}

impl KillLevel {
    pub fn parse(text: &str) -> Result<Self, KillError> {
        match text {
            "K1" => Ok(Self::K1),
            "K2" => Ok(Self::K2),
            "K3" => Ok(Self::K3),
            _ => Err(KillError::Unknown),
        }
    }

    pub fn as_str(self) -> &'static str {
        match self {
            Self::K1 => "K1",
            Self::K2 => "K2",
            Self::K3 => "K3",
        }
    }
}

pub fn apply_kill(current: &str, level: KillLevel) -> Result<(String, bool), KillError> {
    if current == "K3" {
        return Err(KillError::Sealed);
    }
    let revoke = matches!(level, KillLevel::K3);
    Ok((level.as_str().to_string(), revoke))
}

pub fn blocks_new_risk(kill: &str) -> bool {
    matches!(kill, "K1" | "K2")
}

pub fn blocks_all_trading(kill: &str, trading_revoked: bool) -> bool {
    kill == "K3" || trading_revoked
}

#[cfg(test)]
mod tests {
    use super::{KillError, KillLevel, apply_kill, blocks_all_trading, blocks_new_risk};

    #[test]
    fn k1_and_k2_block_new_risk_only() {
        assert!(blocks_new_risk("K1"));
        assert!(!blocks_all_trading("K1", false));
    }

    #[test]
    fn k3_seals_and_revokes() {
        let (state, revoke) = apply_kill("", KillLevel::K3).unwrap();
        assert_eq!(state, "K3");
        assert!(revoke);
        assert!(blocks_all_trading(&state, revoke));
        assert_eq!(apply_kill("K3", KillLevel::K1), Err(KillError::Sealed));
    }
}
