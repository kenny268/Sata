//! Broker truth compared with the local book. A mismatch blocks new risk immediately.
//! This crate does not create fills and it does not grant a verdict.

use std::collections::{BTreeMap, BTreeSet};

use sate_a_verdict::{cmp, PollHook};

pub use sate_a_verdict::POLL_INTERVAL_SECS as POLL_SECS;
pub const DAILY_SECS: u64 = 86_400;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Cause {
    Poll,
    Order,
    Fill,
    Outage,
    Daily,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Outcome {
    Awaiting,
    Waiting,
    Clean,
    Mismatch,
    Ambiguous,
    Outage,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Position {
    pub instrument: String,
    pub side: String,
    pub quantity: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OrderSnap {
    pub correlation_id: String,
    pub state: String,
    pub filled: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct Balance {
    pub equity: String,
    pub margin: String,
    pub currency: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct Book {
    pub positions: Vec<Position>,
    pub orders: Vec<OrderSnap>,
    pub balance: Balance,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BrokerBook {
    pub book: Book,
    pub terms_changed: bool,
    pub withdrawals_frozen: bool,
    pub readable: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Diff {
    pub entity: &'static str,
    pub key: String,
    pub field: &'static str,
    pub local: String,
    pub broker: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Report {
    pub outcome: Outcome,
    pub halt: String,
    pub blocks_new_risk: bool,
    pub allows_retry: bool,
    pub diffs: Vec<Diff>,
    pub corrected: bool,
    pub manufactured_fill: bool,
    pub safe_mode: bool,
    pub reasons: Vec<&'static str>,
}

#[derive(Debug)]
pub struct Engine {
    projection: Book,
    poll: PollHook,
    last_clean: Option<u64>,
    armed: bool,
    last: Report,
}

impl Engine {
    pub fn new(now: u64) -> Self {
        Self {
            projection: Book::default(),
            poll: PollHook::new(now),
            last_clean: None,
            armed: false,
            last: Report {
                outcome: Outcome::Awaiting,
                halt: String::new(),
                blocks_new_risk: true,
                allows_retry: false,
                diffs: Vec::new(),
                corrected: false,
                manufactured_fill: false,
                safe_mode: false,
                reasons: Vec::new(),
            },
        }
    }

    pub fn load(&mut self, book: Book) {
        self.projection = book;
        self.last_clean = None;
        self.last.blocks_new_risk = true;
        self.last.allows_retry = false;
        self.last.outcome = Outcome::Awaiting;
        self.last.corrected = false;
        self.last.diffs.clear();
        self.last.reasons.clear();
        self.last.safe_mode = false;
        if self.armed {
            self.last.halt = "L2".to_string();
        } else {
            self.last.halt.clear();
        }
    }

    pub fn projection(&self) -> &Book {
        &self.projection
    }

    pub fn daily_due(&self, now: u64) -> bool {
        self.last_clean.map(|clean| now >= clean + DAILY_SECS).unwrap_or(true)
    }

    pub fn next_due(&self) -> u64 {
        self.poll.next_due
    }

    /// Copy this engine's halt onto the kernel book. A clean compare clears only an L2 it armed.
    pub fn enforce(&mut self, halt_level: &mut String) {
        if self.last.halt == "L2" {
            self.armed = true;
            *halt_level = "L2".to_string();
            return;
        }
        if self.last.outcome == Outcome::Clean && self.armed && halt_level == "L2" {
            halt_level.clear();
            self.armed = false;
        }
    }

    pub fn compare(&mut self, broker: &BrokerBook, now: u64, cause: Cause) -> Report {
        if cause == Cause::Poll && now < self.poll.next_due {
            let mut waiting = self.last.clone();
            waiting.outcome = Outcome::Waiting;
            return waiting;
        }
        if !broker.readable {
            self.poll.on_failure(now);
            self.last.outcome = Outcome::Outage;
            self.last.blocks_new_risk = true;
            self.last.allows_retry = false;
            self.last.safe_mode = true;
            self.last.corrected = false;
            self.last.manufactured_fill = false;
            self.last.diffs.clear();
            self.last.reasons = vec!["outage"];
            return self.last.clone();
        }
        let compared = differ(&self.projection, &broker.book);
        self.projection = compared.projection;
        self.poll.on_success(now);
        let mut reasons = Vec::new();
        if compared.ambiguous {
            reasons.push("ambiguous");
        } else if !compared.diffs.is_empty() {
            reasons.push("mismatch");
        }
        if broker.terms_changed {
            reasons.push("terms");
        }
        if broker.withdrawals_frozen {
            reasons.push("withdrawals");
        }
        let clean = reasons.is_empty();
        if clean {
            self.last_clean = Some(now);
            self.last = Report {
                outcome: Outcome::Clean,
                halt: String::new(),
                blocks_new_risk: false,
                allows_retry: true,
                diffs: Vec::new(),
                corrected: false,
                manufactured_fill: false,
                safe_mode: false,
                reasons,
            };
        } else {
            self.last = Report {
                outcome: if compared.ambiguous { Outcome::Ambiguous } else { Outcome::Mismatch },
                halt: "L2".to_string(),
                blocks_new_risk: true,
                allows_retry: false,
                diffs: compared.diffs,
                corrected: compared.corrected,
                manufactured_fill: false,
                safe_mode: false,
                reasons,
            };
        }
        self.last.clone()
    }
}

struct Compared {
    projection: Book,
    diffs: Vec<Diff>,
    corrected: bool,
    ambiguous: bool,
}

fn differ(local: &Book, broker: &Book) -> Compared {
    let mut diffs = Vec::new();
    let mut corrected = false;
    let mut ambiguous = false;
    let positions = align_positions(&local.positions, &broker.positions, &mut diffs, &mut corrected, &mut ambiguous);
    let orders = align_orders(&local.orders, &broker.orders, &mut diffs, &mut corrected, &mut ambiguous);
    let balance = align_balance(&local.balance, &broker.balance, &mut diffs, &mut corrected, &mut ambiguous);
    diffs.sort_by(|left, right| {
        (&left.entity, &left.key, &left.field).cmp(&(&right.entity, &right.key, &right.field))
    });
    Compared { projection: Book { positions, orders, balance }, diffs, corrected, ambiguous }
}

fn align_positions(
    local: &[Position],
    broker: &[Position],
    diffs: &mut Vec<Diff>,
    corrected: &mut bool,
    ambiguous: &mut bool,
) -> Vec<Position> {
    let Ok(local_rows) = index(local, |row| row_key(&row.instrument, &row.side)) else {
        *ambiguous = true;
        diffs.push(identity("position"));
        return local.to_vec();
    };
    let Ok(broker_rows) = index(broker, |row| row_key(&row.instrument, &row.side)) else {
        *ambiguous = true;
        diffs.push(identity("position"));
        return local.to_vec();
    };
    let mut merged = BTreeMap::new();
    for key in keys(&local_rows, &broker_rows) {
        match (local_rows.get(&key), broker_rows.get(&key)) {
            (Some(_), None) => {
                *corrected = true;
                diffs.push(presence("position", &key, true));
            }
            (None, Some(row)) => {
                *corrected = true;
                diffs.push(presence("position", &key, false));
                merged.insert(key, row.clone());
            }
            (Some(local_row), Some(broker_row)) => {
                let mut row = local_row.clone();
                match money(&local_row.quantity, &broker_row.quantity) {
                    Rel::Same => {}
                    Rel::Differ => {
                        *corrected = true;
                        diffs.push(field("position", &key, "quantity", &local_row.quantity, &broker_row.quantity));
                        row.quantity = broker_row.quantity.clone();
                    }
                    Rel::Ambiguous => {
                        *ambiguous = true;
                        diffs.push(field("position", &key, "quantity", &local_row.quantity, &broker_row.quantity));
                    }
                }
                merged.insert(key, row);
            }
            (None, None) => {}
        }
    }
    merged.into_values().collect()
}

fn align_orders(
    local: &[OrderSnap],
    broker: &[OrderSnap],
    diffs: &mut Vec<Diff>,
    corrected: &mut bool,
    ambiguous: &mut bool,
) -> Vec<OrderSnap> {
    let Ok(local_rows) = index(local, |row| row_key(&row.correlation_id, "")) else {
        *ambiguous = true;
        diffs.push(identity("order"));
        return local.to_vec();
    };
    let Ok(broker_rows) = index(broker, |row| row_key(&row.correlation_id, "")) else {
        *ambiguous = true;
        diffs.push(identity("order"));
        return local.to_vec();
    };
    let mut merged = BTreeMap::new();
    for key in keys(&local_rows, &broker_rows) {
        match (local_rows.get(&key), broker_rows.get(&key)) {
            (Some(_), None) => {
                *corrected = true;
                diffs.push(presence("order", &key, true));
            }
            (None, Some(row)) => {
                *corrected = true;
                diffs.push(presence("order", &key, false));
                merged.insert(key, row.clone());
            }
            (Some(local_row), Some(broker_row)) => {
                let mut row = local_row.clone();
                match text(&local_row.state, &broker_row.state) {
                    Rel::Same => {}
                    Rel::Differ => {
                        *corrected = true;
                        diffs.push(field("order", &key, "state", &local_row.state, &broker_row.state));
                        row.state = broker_row.state.clone();
                    }
                    Rel::Ambiguous => {
                        *ambiguous = true;
                        diffs.push(field("order", &key, "state", &local_row.state, &broker_row.state));
                    }
                }
                match money(&local_row.filled, &broker_row.filled) {
                    Rel::Same => {}
                    Rel::Differ => {
                        *corrected = true;
                        diffs.push(field("order", &key, "filled", &local_row.filled, &broker_row.filled));
                        row.filled = broker_row.filled.clone();
                    }
                    Rel::Ambiguous => {
                        *ambiguous = true;
                        diffs.push(field("order", &key, "filled", &local_row.filled, &broker_row.filled));
                    }
                }
                merged.insert(key, row);
            }
            (None, None) => {}
        }
    }
    merged.into_values().collect()
}

fn align_balance(
    local: &Balance,
    broker: &Balance,
    diffs: &mut Vec<Diff>,
    corrected: &mut bool,
    ambiguous: &mut bool,
) -> Balance {
    let mut next = local.clone();
    let mut apply = |name: &'static str, local_value: &str, broker_value: &str, slot: &mut String| {
        match money(local_value, broker_value) {
            Rel::Same => {}
            Rel::Differ => {
                *corrected = true;
                diffs.push(field("balance", "account", name, local_value, broker_value));
                *slot = broker_value.to_string();
            }
            Rel::Ambiguous => {
                *ambiguous = true;
                diffs.push(field("balance", "account", name, local_value, broker_value));
            }
        }
    };
    apply("equity", &local.equity, &broker.equity, &mut next.equity);
    apply("margin", &local.margin, &broker.margin, &mut next.margin);
    match text(&local.currency, &broker.currency) {
        Rel::Same => {}
        Rel::Differ => {
            *corrected = true;
            diffs.push(field("balance", "account", "currency", &local.currency, &broker.currency));
            next.currency = broker.currency.clone();
        }
        Rel::Ambiguous => {
            *ambiguous = true;
            diffs.push(field("balance", "account", "currency", &local.currency, &broker.currency));
        }
    }
    next
}

fn index<T: Clone>(rows: &[T], key_of: impl Fn(&T) -> String) -> Result<BTreeMap<String, T>, ()> {
    let mut indexed = BTreeMap::new();
    for row in rows {
        let key = key_of(row);
        if blank(&key) || indexed.insert(key, row.clone()).is_some() {
            return Err(());
        }
    }
    Ok(indexed)
}

fn keys<T>(local: &BTreeMap<String, T>, broker: &BTreeMap<String, T>) -> BTreeSet<String> {
    local.keys().chain(broker.keys()).cloned().collect()
}

fn row_key(left: &str, right: &str) -> String {
    if right.is_empty() { left.to_string() } else { format!("{left}:{right}") }
}

fn identity(entity: &'static str) -> Diff {
    Diff { entity, key: String::new(), field: "identity", local: "duplicate".to_string(), broker: "duplicate".to_string() }
}

fn presence(entity: &'static str, key: &str, local_only: bool) -> Diff {
    Diff {
        entity,
        key: key.to_string(),
        field: "present",
        local: if local_only { "yes" } else { "no" }.to_string(),
        broker: if local_only { "no" } else { "yes" }.to_string(),
    }
}

fn field(entity: &'static str, key: &str, name: &'static str, local: &str, broker: &str) -> Diff {
    Diff {
        entity,
        key: key.to_string(),
        field: name,
        local: local.to_string(),
        broker: broker.to_string(),
    }
}

enum Rel { Same, Differ, Ambiguous }

fn money(local: &str, broker: &str) -> Rel {
    if local.is_empty() || broker.is_empty() {
        return Rel::Ambiguous;
    }
    match cmp(local, broker) {
        Some(std::cmp::Ordering::Equal) => Rel::Same,
        Some(_) => Rel::Differ,
        None => Rel::Ambiguous,
    }
}

fn text(local: &str, broker: &str) -> Rel {
    if local.is_empty() || broker.is_empty() {
        return Rel::Ambiguous;
    }
    if local == broker { Rel::Same } else { Rel::Differ }
}

fn blank(value: &str) -> bool {
    value.is_empty() || value.chars().any(char::is_whitespace)
}

#[cfg(test)]
mod tests {
    use super::{Balance, Book, BrokerBook, Cause, Engine, OrderSnap, Outcome, Position, DAILY_SECS, POLL_SECS};

    fn position(quantity: &str) -> Position {
        Position { instrument: "EURUSD".to_string(), side: "BUY".to_string(), quantity: quantity.to_string() }
    }

    fn book(quantity: &str) -> Book {
        Book {
            positions: vec![position(quantity)],
            orders: vec![OrderSnap {
                correlation_id: "A:i-1".to_string(),
                state: "Submitted".to_string(),
                filled: "0".to_string(),
            }],
            balance: Balance { equity: "1000".to_string(), margin: "25".to_string(), currency: "USD".to_string() },
        }
    }

    fn broker(quantity: &str) -> BrokerBook {
        BrokerBook { book: book(quantity), terms_changed: false, withdrawals_frozen: false, readable: true }
    }

    #[test]
    fn the_read_poll_is_five_seconds() {
        assert_eq!(POLL_SECS, 5);
    }

    #[test]
    fn c3_mismatch_blocks_immediately_and_one_clean_compare_resumes() {
        let mut engine = Engine::new(0);
        let mut foreign = "L2".to_string();
        let mut quiet = Engine::new(0);
        quiet.load(book("1"));
        assert_eq!(quiet.compare(&broker("1"), 0, Cause::Order).outcome, Outcome::Clean);
        quiet.enforce(&mut foreign);
        assert_eq!(foreign, "L2");
        assert!(engine.daily_due(0));
        let waiting = engine.compare(&broker("1"), 0, Cause::Poll);
        assert_eq!(waiting.outcome, Outcome::Waiting);
        assert!(waiting.blocks_new_risk);
        assert!(!waiting.allows_retry);
        engine.load(book("1"));
        let mismatch = engine.compare(&broker("2"), 0, Cause::Order);
        assert_eq!(mismatch.outcome, Outcome::Mismatch);
        assert_eq!(mismatch.halt, "L2");
        assert!(mismatch.blocks_new_risk);
        assert!(!mismatch.allows_retry);
        assert!(mismatch.corrected);
        assert!(!mismatch.manufactured_fill);
        assert_eq!(mismatch.diffs[0].field, "quantity");
        assert_eq!(mismatch.diffs[0].local, "1");
        assert_eq!(mismatch.diffs[0].broker, "2");
        assert_eq!(engine.projection().positions[0].quantity, "2");
        let mut halt = String::new();
        engine.enforce(&mut halt);
        assert_eq!(halt, "L2");
        assert_eq!(engine.next_due(), POLL_SECS);
        let early = engine.compare(&broker("2"), 1, Cause::Poll);
        assert_eq!(early.outcome, Outcome::Waiting);
        assert_eq!(early.halt, "L2");
        let clean = engine.compare(&broker("2"), 1, Cause::Daily);
        assert_eq!(clean.outcome, Outcome::Clean);
        assert!(clean.halt.is_empty());
        assert!(!clean.blocks_new_risk);
        assert!(clean.allows_retry);
        engine.enforce(&mut halt);
        assert!(halt.is_empty());
        assert!(!engine.daily_due(1));
        assert!(engine.daily_due(1 + DAILY_SECS));
        engine.load(book("9"));
        assert!(engine.daily_due(1));
        assert!(!engine.compare(&broker("9"), 2, Cause::Poll).allows_retry);
        let reloaded = engine.compare(&broker("9"), 2, Cause::Order);
        assert_eq!(reloaded.outcome, Outcome::Clean);
        assert!(reloaded.allows_retry);
    }

    #[test]
    fn a_terms_change_and_frozen_withdrawals_block_without_a_new_cap() {
        let mut terms = Engine::new(0);
        terms.load(book("1"));
        let mut changed = broker("1");
        changed.terms_changed = true;
        let report = terms.compare(&changed, 0, Cause::Fill);
        assert_eq!(report.halt, "L2");
        assert!(report.reasons.contains(&"terms"));
        assert!(!report.corrected);
        assert_eq!(terms.projection().positions[0].quantity, "1");
        assert!(!report.allows_retry);

        let mut frozen = Engine::new(0);
        frozen.load(book("1"));
        let mut held = broker("1");
        held.withdrawals_frozen = true;
        let report = frozen.compare(&held, 0, Cause::Order);
        assert_eq!(report.halt, "L2");
        assert!(report.reasons.contains(&"withdrawals"));
        assert_eq!(frozen.projection().balance.equity, "1000");
        assert!(!report.allows_retry);
    }

    #[test]
    fn an_unknown_quantity_stays_ambiguous_and_an_outage_keeps_the_book() {
        let mut engine = Engine::new(0);
        engine.load(book("1"));
        let mut unknown = broker("");
        unknown.book.positions[0].quantity.clear();
        let report = engine.compare(&unknown, 0, Cause::Order);
        assert_eq!(report.outcome, Outcome::Ambiguous);
        assert_eq!(report.halt, "L2");
        assert_eq!(engine.projection().positions[0].quantity, "1");
        assert!(!report.manufactured_fill);
        let mut dark = broker("1");
        dark.readable = false;
        let outage = engine.compare(&dark, 1, Cause::Outage);
        assert_eq!(outage.outcome, Outcome::Outage);
        assert!(outage.safe_mode);
        assert_eq!(outage.halt, "L2");
        assert_eq!(engine.projection().positions[0].quantity, "1");
        assert!(!outage.allows_retry);
    }

    #[test]
    fn a_broker_fill_updates_the_projection_and_does_not_create_a_fill() {
        let mut engine = Engine::new(0);
        engine.load(book("1"));
        let mut reported = broker("1");
        reported.book.orders[0].state = "Filled".to_string();
        reported.book.orders[0].filled = "1.0".to_string();
        let report = engine.compare(&reported, 0, Cause::Fill);
        assert!(report.corrected);
        assert!(!report.manufactured_fill);
        assert_eq!(engine.projection().orders[0].state, "Filled");
        assert_eq!(engine.projection().orders[0].filled, "1.0");
        assert!(!report.allows_retry);
    }

    #[test]
    fn equal_decimals_match_and_a_missing_position_is_a_field_diff() {
        let mut engine = Engine::new(0);
        engine.load(book("1"));
        let mut same = broker("1.0");
        same.book.positions[0].quantity = "1.0".to_string();
        let clean = engine.compare(&same, 0, Cause::Order);
        assert_eq!(clean.outcome, Outcome::Clean);
        assert!(clean.diffs.is_empty());
        let mut gone = broker("1");
        gone.book.positions.clear();
        let missing = engine.compare(&gone, 0, Cause::Order);
        assert_eq!(missing.outcome, Outcome::Mismatch);
        assert_eq!(missing.halt, "L2");
        assert!(missing.blocks_new_risk);
        assert_eq!(missing.diffs[0].field, "present");
        assert!(engine.projection().positions.is_empty());
        let mut cash = book("1");
        cash.balance.equity = "1000".to_string();
        engine.load(cash);
        let mut marked = broker("1");
        marked.book.balance.equity = "900".to_string();
        let balance = engine.compare(&marked, 0, Cause::Order);
        assert_eq!(balance.halt, "L2");
        assert_eq!(engine.projection().balance.equity, "900");
        assert!(!balance.manufactured_fill);
    }
}
