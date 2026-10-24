//! KERNEL-A verdict path. Checks run in §6.4 order and short-circuit.
//! Latency is recorded. The no-heap p99 target is not claimed from this path.

mod checkin;
mod decimal;
mod engine;
mod halt;
mod kill;
mod ladder;
mod mode;
mod session;
mod slippage;

pub use decimal::{add, cmp, sub};
pub use engine::{Check, Decision, Intent, KernelBook, MinLotPolicy, Verdict, KERNEL_VERSION, decide};
pub use halt::{read as read_halt, HaltError, HaltRecord};
pub use session::{MockAdapter, PollHook, Session, POLL_INTERVAL_SECS, STAGING_SECS, approved};
pub use slippage::{budget as slippage_budget, within_budget, SlippageWindow, WINDOW as SLIPPAGE_WINDOW};
pub use kill::{apply_kill, blocks_all_trading as kill_blocks_all, blocks_new_risk as kill_blocks_new, KillError, KillLevel};
pub use ladder::{blocks_new_risk as halt_blocks_new, escalate, revokes_trading, HaltLevel, HaltTrigger};
pub use mode::{badge as mode_badge, blocks_new_risk as mode_blocks_new, transition as mode_transition, ModeError, ModeEvent};
pub use checkin::{
    days_without as checkin_days_without, record as record_checkin, set_away as set_checkin_away, tier as checkin_tier,
    CheckinBook, CheckinChannel, CheckinError, CheckinTier,
};

#[cfg(test)]
mod checkin_ladder_tests;

#[cfg(test)]
mod halt_ladder_tests;

#[cfg(test)]
mod order_tests;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct VerdictInputs {
    pub group_scope: String,
    pub rcb_version: u64,
    pub constitution_version: u64,
    pub effective_limit: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum InputError {
    Scope,
    MissingRcbVersion,
    MissingConstitution,
    MissingLimit,
    ConstitutionMismatch,
}

impl VerdictInputs {
    /// Rejects a missing RCB version or constitution version.
    pub fn try_new(
        group_scope: &str,
        rcb_version: u64,
        constitution_version: u64,
        effective_limit: &str,
    ) -> Result<Self, InputError> {
        if group_scope != "A" && group_scope != "B" {
            return Err(InputError::Scope);
        }
        if rcb_version == 0 {
            return Err(InputError::MissingRcbVersion);
        }
        if constitution_version == 0 {
            return Err(InputError::MissingConstitution);
        }
        if effective_limit.is_empty() {
            return Err(InputError::MissingLimit);
        }
        Ok(Self {
            group_scope: group_scope.to_string(),
            rcb_version,
            constitution_version,
            effective_limit: effective_limit.to_string(),
        })
    }

    /// The trade path uses the constitution version loaded at startup.
    pub fn for_loaded_constitution(&self, loaded_version: u64) -> Result<(), InputError> {
        if self.constitution_version != loaded_version {
            return Err(InputError::ConstitutionMismatch);
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::{InputError, VerdictInputs};

    #[test]
    fn missing_rcb_version_is_rejected() {
        let err = VerdictInputs::try_new("A", 0, 1, "100").unwrap_err();
        assert_eq!(err, InputError::MissingRcbVersion);
    }

    #[test]
    fn a_loaded_constitution_must_match() {
        let missing = VerdictInputs::try_new("A", 2, 0, "180").unwrap_err();
        assert_eq!(missing, InputError::MissingConstitution);
        let inputs = VerdictInputs::try_new("A", 2, 1, "180").unwrap();
        assert_eq!(inputs.for_loaded_constitution(1), Ok(()));
        let mismatch = inputs.for_loaded_constitution(2).unwrap_err();
        assert_eq!(mismatch, InputError::ConstitutionMismatch);
    }
}
