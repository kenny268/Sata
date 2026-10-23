//! Staging session, mock adapter, and the 5 second read poll.

use std::collections::BTreeMap;
use std::path::Path;

use crate::engine::{Decision, Intent, KernelBook, Verdict, decide};
use crate::kill::{apply_kill, KillLevel};
use crate::ladder::{escalate, revokes_trading, HaltLevel, HaltTrigger};
use crate::mode::{transition as mode_transition, ModeEvent};
use crate::slippage::within_budget;
use crate::checkin::{self, CheckinChannel};
use crate::halt::{self, HaltError};

pub const POLL_INTERVAL_SECS: u64 = 5;
pub const STAGING_SECS: u64 = 86_400;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PollHook {
    pub next_due: u64,
    pub safe_mode: bool,
    pub failures: u32,
}

impl PollHook {
    pub fn new(now: u64) -> Self {
        Self { next_due: now + POLL_INTERVAL_SECS, safe_mode: false, failures: 0 }
    }

    pub fn on_success(&mut self, now: u64) {
        self.safe_mode = false;
        self.failures = 0;
        self.next_due = now + POLL_INTERVAL_SECS;
    }

    pub fn on_failure(&mut self, now: u64) {
        self.safe_mode = true;
        self.failures += 1;
        self.next_due = now + POLL_INTERVAL_SECS;
    }
}

#[derive(Debug, Default, Clone)]
pub struct MockAdapter {
    pub submits: Vec<String>,
}

impl MockAdapter {
    pub fn submit(&mut self, verdict: &Verdict) -> Result<(), &'static str> {
        if !verdict.persisted {
            return Err("verdict is not in the fact log");
        }
        if !verdict.decision.allows_broker_submit() {
            return Err("no broker order without an allow verdict");
        }
        self.submits.push(verdict.intent_id.clone());
        Ok(())
    }
}

#[derive(Debug)]
pub struct Session {
    pub book: KernelBook,
    pub adapter: MockAdapter,
    pub poll: PollHook,
    pub started_at: u64,
    pub intents: u64,
    verdicts: Vec<Verdict>,
    seen: BTreeMap<String, usize>,
}

impl Session {
    /// A missing halt file starts clear. A malformed file refuses the restart.
    pub fn resume(mut book: KernelBook, path: &Path, now: u64) -> Result<Self, HaltError> {
        match halt::read(path) {
            Ok(record) => halt::apply(&record, &mut book),
            Err(HaltError::Missing) => {}
            Err(error) => return Err(error),
        }
        Ok(Self::open(book, now))
    }

    pub fn open(book: KernelBook, now: u64) -> Self {
        let poll = PollHook::new(now);
        Self {
            book,
            adapter: MockAdapter::default(),
            poll,
            started_at: now,
            intents: 0,
            verdicts: Vec::new(),
            seen: BTreeMap::new(),
        }
    }

    pub fn on_poll(&mut self, now: u64, ok: bool) {
        if ok {
            self.poll.on_success(now);
        } else {
            self.poll.on_failure(now);
        }
        self.book.safe_mode = self.poll.safe_mode;
    }

    /// Every call returns a verdict. A repeated intent id returns the first one.
    pub fn handle(&mut self, intent: &Intent, issued_at: &str) -> Verdict {
        if let Some(index) = self.seen.get(&intent.intent_id) {
            return self.verdicts[*index].clone();
        }
        self.intents += 1;
        let mut verdict = decide(&self.book, intent, issued_at);
        if verdict.arm_halt == Some("L2") {
            self.book.halt_level = "L2".to_string();
        } else if verdict.arm_halt == Some("L1") && self.book.halt_level.is_empty() {
            self.book.halt_level = "L1".to_string();
            self.book.slippage_l1_armed = true;
        }
        self.seen.insert(intent.intent_id.clone(), self.verdicts.len());
        self.verdicts.push(verdict.clone());
        verdict.persisted = false;
        verdict
    }

    pub fn submit_persisted(&mut self, verdict: &Verdict) -> Result<(), &'static str> {
        self.adapter.submit(verdict)
    }

    pub fn verdict_count(&self) -> u64 {
        u64::try_from(self.verdicts.len()).unwrap_or(u64::MAX)
    }

    pub fn gate_met(&self, now: u64) -> bool {
        self.intents > 0 && self.verdict_count() == self.intents && now.saturating_sub(self.started_at) >= STAGING_SECS
    }

    pub fn save_halt(&self, path: &Path) -> Result<(), HaltError> {
        halt::save(path, &self.book)
    }

    pub fn load_halt(&mut self, path: &Path) -> Result<(), HaltError> {
        halt::load(path, &mut self.book)
    }

    pub fn record_slippage(&mut self, within_budget: bool) {
        self.book.slippage_window.record(within_budget);
        self.sync_slippage_halt();
    }

    /// PERF measurement on a fill price. An unknown instrument records a breach.
    pub fn measure_slippage(&mut self, instrument: &str, expected: &str, fill: &str) -> bool {
        let ok = within_budget(instrument, expected, fill);
        self.book.slippage_window.record(ok);
        self.sync_slippage_halt();
        ok
    }

    /// L1 while the rolling window holds a breach. Recovery is that window, not an unset session count.
    fn sync_slippage_halt(&mut self) {
        if self.book.slippage_window.breached() {
            if self.book.halt_level.is_empty() {
                self.escalate_halt(HaltTrigger::SlippageBudget);
                self.book.slippage_l1_armed = true;
            }
            return;
        }
        if self.book.slippage_l1_armed && self.book.halt_level == "L1" {
            self.book.halt_level.clear();
            self.book.slippage_l1_armed = false;
        }
    }

    pub fn apply_kill(&mut self, level: KillLevel) -> Result<(), crate::kill::KillError> {
        let (state, revoke) = apply_kill(&self.book.kill_state, level)?;
        self.book.kill_state = state;
        self.book.trading_revoked |= revoke;
        Ok(())
    }

    pub fn escalate_halt(&mut self, trigger: HaltTrigger) {
        let current = HaltLevel::parse(&self.book.halt_level);
        let next = escalate(current, trigger);
        self.book.halt_level = next.as_str().to_string();
        if revokes_trading(next) {
            self.book.trading_revoked = true;
        }
    }

    pub fn transition_mode(&mut self, event: ModeEvent) -> Result<(), crate::mode::ModeError> {
        let next = mode_transition(&self.book.mode, event)?;
        self.book.mode = next.to_string();
        Ok(())
    }

    pub fn record_checkin(&mut self, channel: CheckinChannel) {
        checkin::record(&mut self.book.checkin, channel);
    }

    pub fn set_checkin_away(&mut self, days: u32) -> Result<(), checkin::CheckinError> {
        checkin::set_away(&mut self.book.checkin, days)
    }

    pub fn advance_checkin_day(&mut self, day: u64) {
        self.book.checkin.current_day = day;
    }
}

pub fn approved(decision: Decision) -> bool {
    decision.allows_broker_submit()
}
