//! Trading mode state machine (**A-P0-15**, **A-MOD-01**).

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ModeError {
    Unknown,
    Blocked,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ModeEvent {
    LiveToSim,
    EnterManageOnly,
    EnterHalted,
    ReArmToSim,
    ArmLiveL1,
}

pub fn normalize(mode: &str) -> Result<&'static str, ModeError> {
    match mode {
        "SIM" => Ok("SIM"),
        "LIVE-L1" => Ok("LIVE-L1"),
        "LIVE-L2" => Ok("LIVE-L2"),
        "LIVE-L3" => Ok("LIVE-L3"),
        "MANAGE_ONLY" => Ok("MANAGE_ONLY"),
        "HALTED" => Ok("HALTED"),
        _ => Err(ModeError::Unknown),
    }
}

pub fn transition(current: &str, event: ModeEvent) -> Result<&'static str, ModeError> {
    normalize(current)?;
    match (current, event) {
        ("SIM", ModeEvent::ArmLiveL1) => Ok("LIVE-L1"),
        ("LIVE-L1" | "LIVE-L2" | "LIVE-L3", ModeEvent::LiveToSim) => Ok("MANAGE_ONLY"),
        ("LIVE-L1" | "LIVE-L2" | "LIVE-L3", ModeEvent::EnterManageOnly) => Ok("MANAGE_ONLY"),
        (_, ModeEvent::EnterHalted) => Ok("HALTED"),
        ("MANAGE_ONLY", ModeEvent::ReArmToSim) => Ok("SIM"),
        ("HALTED", ModeEvent::ReArmToSim) => Ok("SIM"),
        ("LIVE-L2" | "LIVE-L3", ModeEvent::ArmLiveL1) => Err(ModeError::Blocked),
        _ => Err(ModeError::Blocked),
    }
}

pub fn blocks_new_risk(mode: &str) -> bool {
    matches!(mode, "MANAGE_ONLY" | "HALTED")
}

pub fn badge(mode: &str) -> Option<(&'static str, &'static str)> {
    match mode {
        "SIM" => Some(("blue", "A-SIM")),
        "LIVE-L1" | "LIVE-L2" | "LIVE-L3" => Some(("red", "A-LIVE")),
        "MANAGE_ONLY" => Some(("amber", "A-MANAGE")),
        "HALTED" => Some(("red", "A-HALTED")),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::{ModeError, ModeEvent, badge, blocks_new_risk, transition};

    #[test]
    fn live_to_sim_enters_manage_only() {
        assert_eq!(transition("LIVE-L1", ModeEvent::LiveToSim).unwrap(), "MANAGE_ONLY");
        assert!(blocks_new_risk("MANAGE_ONLY"));
    }

    #[test]
    fn halted_and_manage_only_block_new_risk() {
        assert!(blocks_new_risk("HALTED"));
        assert!(!blocks_new_risk("SIM"));
    }

    #[test]
    fn badges_follow_a_mod_04() {
        assert_eq!(badge("SIM"), Some(("blue", "A-SIM")));
        assert_eq!(badge("LIVE-L1"), Some(("red", "A-LIVE")));
    }

    #[test]
    fn live_l2_cannot_skip_to_l1_without_decision() {
        assert_eq!(transition("LIVE-L2", ModeEvent::ArmLiveL1), Err(ModeError::Blocked));
    }
}
