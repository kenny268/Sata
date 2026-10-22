//! Staging session, mock adapter, and the 5 second read poll.

use std::collections::BTreeMap;
use std::path::Path;

use crate::engine::{Decision, Intent, KernelBook, Verdict, decide};
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
}

pub fn approved(decision: Decision) -> bool {
    decision.allows_broker_submit()
}
