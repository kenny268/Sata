//! Automatic halt ladder **L1–L4** (**§9.1**, **A-P0-14**).

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum HaltLevel {
    None,
    L1,
    L2,
    L3,
    L4,
}

impl HaltLevel {
    pub fn parse(text: &str) -> Self {
        match text {
            "L1" => Self::L1,
            "L2" => Self::L2,
            "L3" => Self::L3,
            "L4" => Self::L4,
            _ => Self::None,
        }
    }

    pub fn as_str(self) -> &'static str {
        match self {
            Self::None => "",
            Self::L1 => "L1",
            Self::L2 => "L2",
            Self::L3 => "L3",
            Self::L4 => "L4",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HaltTrigger {
    SlippageBudget,
    FeedDegraded,
    DailyLoss,
    ReconMismatch,
    FingerprintMismatch,
    HeartbeatLost,
    Drawdown,
    MarginStress,
    RepeatedL2,
    OpsHeartbeat,
    AccountChange,
}

pub fn escalate(current: HaltLevel, trigger: HaltTrigger) -> HaltLevel {
    let target = match trigger {
        HaltTrigger::SlippageBudget | HaltTrigger::FeedDegraded => HaltLevel::L1,
        HaltTrigger::DailyLoss
        | HaltTrigger::ReconMismatch
        | HaltTrigger::FingerprintMismatch
        | HaltTrigger::HeartbeatLost => HaltLevel::L2,
        HaltTrigger::Drawdown | HaltTrigger::MarginStress | HaltTrigger::RepeatedL2 => HaltLevel::L3,
        HaltTrigger::OpsHeartbeat | HaltTrigger::AccountChange => HaltLevel::L4,
    };
    if target > current { target } else { current }
}

pub fn blocks_new_risk(level: HaltLevel) -> bool {
    matches!(level, HaltLevel::L2 | HaltLevel::L3 | HaltLevel::L4)
}

pub fn revokes_trading(level: HaltLevel) -> bool {
    matches!(level, HaltLevel::L4)
}

#[cfg(test)]
mod tests {
    use super::{HaltLevel, HaltTrigger, blocks_new_risk, escalate, revokes_trading};

    #[test]
    fn hl01_slippage_is_l1_and_hl07_drawdown_is_l3() {
        assert_eq!(escalate(HaltLevel::None, HaltTrigger::SlippageBudget), HaltLevel::L1);
        assert!(!blocks_new_risk(HaltLevel::L1));
        assert_eq!(escalate(HaltLevel::L1, HaltTrigger::Drawdown), HaltLevel::L3);
        assert!(blocks_new_risk(HaltLevel::L3));
    }

    #[test]
    fn hl_f_ops_heartbeat_is_l4_and_revokes() {
        let level = escalate(HaltLevel::L2, HaltTrigger::OpsHeartbeat);
        assert_eq!(level, HaltLevel::L4);
        assert!(revokes_trading(level));
    }
}
