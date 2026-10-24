//! Ordered §6.4 checks. A failing risk-increasing check stops the rest.

use std::time::Instant;

use crate::decimal::{self, cmp, floor_to_step, mul_div, on_step, percent_of};
use crate::slippage::SlippageWindow;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum MinLotPolicy {
    #[default]
    Reject,
    /// Owner-selected path when **A-DEC-01** is resolved. Stays off until then.
    UseMinLot,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Decision {
    Allow,
    AllowWithSize,
    Reject,
    Throttle,
}

impl Decision {
    pub fn allows_broker_submit(self) -> bool {
        matches!(self, Self::Allow | Self::AllowWithSize)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Check {
    pub name: &'static str,
    pub value: String,
    pub limit: String,
    pub passed: bool,
}

pub const KERNEL_VERSION: &str = "0.1.0";

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Verdict {
    pub intent_id: String,
    pub kernel_version: String,
    pub decision: Decision,
    pub reason: &'static str,
    pub size: String,
    pub checks: Vec<Check>,
    pub constitution_version: u64,
    pub rcb_version: u64,
    pub halt_level: String,
    pub kill_state: String,
    pub latency_us: u64,
    pub issued_at: String,
    pub arm_halt: Option<&'static str>,
    pub persisted: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct KernelBook {
    pub mode: String,
    pub universe: Vec<String>,
    pub halt_level: String,
    pub kill_state: String,
    pub fingerprint: String,
    pub rcb_version: u64,
    pub constitution_version: u64,
    pub constitution_pin: u64,
    pub effective_limit: String,
    pub equity: String,
    pub daily_loss: String,
    pub daily_loss_limit: String,
    pub drawdown: String,
    pub drawdown_limit: String,
    pub max_risk_pct: String,
    pub vol_scale: String,
    pub ramp_factor: String,
    pub kelly_ceiling: String,
    pub spread: String,
    pub commission: String,
    pub swap: String,
    pub modeled_slippage: String,
    pub wednesday_triple: bool,
    pub max_notional_x: String,
    pub open_notional: String,
    pub leverage_used: String,
    pub max_leverage: String,
    pub concentration: String,
    pub concentration_limit: String,
    pub margin_level: String,
    pub margin_floor: String,
    pub news_blackout: bool,
    pub swap_guard: bool,
    pub rate_limited: bool,
    pub require_protective_stop: bool,
    pub min_lot: String,
    pub lot_step: String,
    pub min_lot_policy: MinLotPolicy,
    pub slippage_window: SlippageWindow,
    pub ramp_open: bool,
    pub safe_mode: bool,
    pub market_stale: bool,
    pub trading_revoked: bool,
    pub checkin: crate::checkin::CheckinBook,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Intent {
    pub intent_id: String,
    pub group: String,
    pub account_mode: String,
    pub instrument: String,
    pub quantity: String,
    pub notional: String,
    pub risk_amount: String,
    pub protective_stop: String,
    pub fingerprint: String,
    pub reduce_only: bool,
    pub abstain: bool,
}

pub fn decide(book: &KernelBook, intent: &Intent, issued_at: &str) -> Verdict {
    let started = Instant::now();
    let mut checks = Vec::new();
    let outcome = evaluate(book, intent, &mut checks);
    Verdict {
        intent_id: intent.intent_id.clone(),
        kernel_version: KERNEL_VERSION.to_string(),
        decision: outcome.0,
        reason: outcome.1,
        size: outcome.2,
        checks,
        constitution_version: book.constitution_version,
        rcb_version: book.rcb_version,
        halt_level: book.halt_level.clone(),
        kill_state: book.kill_state.clone(),
        latency_us: u64::try_from(started.elapsed().as_micros()).unwrap_or(u64::MAX),
        issued_at: issued_at.to_string(),
        arm_halt: outcome.3,
        persisted: false,
    }
}

fn evaluate(
    book: &KernelBook,
    intent: &Intent,
    checks: &mut Vec<Check>,
) -> (Decision, &'static str, String, Option<&'static str>) {
    if intent.intent_id.is_empty() || intent.group != "A" {
        return reject(checks, "scope", &intent.group, "A", "scope", None);
    }
    if intent.abstain {
        return reject(checks, "advisory", "abstain", "zero_view", "abstain", None);
    }
    if book.rcb_version == 0 || book.constitution_version == 0 {
        return reject(checks, "scope", "0", "pinned", "unbound", None);
    }
    if book.constitution_version != book.constitution_pin {
        let loaded = book.constitution_version.to_string();
        let pin = book.constitution_pin.to_string();
        return reject(checks, "constitution", &loaded, &pin, "constitution", None);
    }
    if book.kill_state == "K3" || book.trading_revoked {
        let value = if book.kill_state == "K3" { "K3" } else { "L4" };
        return reject(checks, "halt_kill", value, "", "revoked", None);
    }
    if intent.reduce_only {
        push(checks, "halt_kill", book.halt_level.as_str(), book.kill_state.as_str(), true);
        return match fingerprint(book, intent, checks) {
            Some(verdict) => verdict,
            None => (Decision::Allow, "", String::new(), None),
        };
    }
    if book.safe_mode {
        return reject(checks, "halt_kill", "safe_mode", "", "safe_mode", None);
    }
    if is_blocking_halt(book) {
        let value = if book.kill_state.is_empty() { book.halt_level.as_str() } else { book.kill_state.as_str() };
        let reason = if book.kill_state.is_empty() { "halt" } else { "kill" };
        return reject(checks, "halt_kill", value, "", reason, None);
    }
    push(checks, "halt_kill", book.halt_level.as_str(), book.kill_state.as_str(), true);
    if let Some(verdict) = fingerprint(book, intent, checks) {
        return verdict;
    }
    if book.market_stale {
        return reject(checks, "freshness", "stale", "fresh", "stale", None);
    }
    if intent.account_mode == "LIVE" && !intent.reduce_only {
        if let Some(verdict) = checkin_gate(book, intent, checks) {
            return verdict;
        }
    }
    if let Some(verdict) = mode_gate(book, intent, checks) {
        return verdict;
    }
    let mut size = String::new();
    if let Some(verdict) = rcb_gate(book, intent, checks, &mut size) {
        return verdict;
    }
    if let Some(verdict) = drawdown_gate(book, checks) {
        return verdict;
    }
    if let Some(verdict) = sizing_gate(book, intent, checks, &mut size) {
        return verdict;
    }
    if let Some(verdict) = risk_gate(book, intent, checks, &size) {
        return verdict;
    }
    if let Some(verdict) = notional_gate(book, intent, checks, &mut size) {
        return verdict;
    }
    if let Some(verdict) = concentration_gate(book, checks) {
        return verdict;
    }
    if let Some(verdict) = margin_gate(book, checks) {
        return verdict;
    }
    if let Some(verdict) = blackout_gate(book, checks) {
        return verdict;
    }
    if let Some(verdict) = cost_gate(book, checks) {
        return verdict;
    }
    if book.halt_level == "L1" || book.slippage_window.breached() {
        if let Some(verdict) = halve_for_l1(book, intent, checks, &mut size) {
            return verdict;
        }
    }
    if book.rate_limited {
        push(checks, "rate_limit", "limited", "", false);
        return (Decision::Throttle, "rate_limit", size, None);
    }
    push(checks, "rate_limit", "clear", "", true);
    if size.is_empty() {
        (Decision::Allow, "", String::new(), None)
    } else {
        (Decision::AllowWithSize, "", size, None)
    }
}

fn fingerprint(
    book: &KernelBook,
    intent: &Intent,
    checks: &mut Vec<Check>,
) -> Option<(Decision, &'static str, String, Option<&'static str>)> {
    if intent.fingerprint != book.fingerprint {
        return Some(reject(checks, "fingerprint", &intent.fingerprint, &book.fingerprint, "fingerprint", Some("L2")));
    }
    push(checks, "fingerprint", &intent.fingerprint, &book.fingerprint, true);
    None
}

fn checkin_gate(
    book: &KernelBook,
    _intent: &Intent,
    checks: &mut Vec<Check>,
) -> Option<(Decision, &'static str, String, Option<&'static str>)> {
    use crate::checkin::{days_without, tier, CheckinTier};
    let days = days_without(&book.checkin);
    match tier(&book.checkin) {
        CheckinTier::Flatten => {
            return Some(reject(
                checks,
                "checkin",
                &days.to_string(),
                "flatten",
                "checkin_flatten",
                None,
            ));
        }
        CheckinTier::ManageOnly => {
            return Some(reject(
                checks,
                "checkin",
                &days.to_string(),
                "manage",
                "checkin",
                None,
            ));
        }
        CheckinTier::Reminder => {
            push(checks, "checkin", &days.to_string(), "reminder", true);
        }
        CheckinTier::Ok => {
            push(checks, "checkin", &days.to_string(), "ok", true);
        }
    }
    None
}

fn mode_gate(
    book: &KernelBook,
    intent: &Intent,
    checks: &mut Vec<Check>,
) -> Option<(Decision, &'static str, String, Option<&'static str>)> {
    if book.mode == "LIVE-L2" || book.mode == "LIVE-L3" {
        return Some(reject(checks, "mode_universe", &book.mode, "A-DEC-02", "a_dec_02", None));
    }
    if book.mode == "MANAGE_ONLY" || book.mode == "HALTED" {
        return Some(reject(checks, "mode_universe", &book.mode, "reduce", "manage_only", None));
    }
    let live = book.mode.starts_with("LIVE");
    if (live && intent.account_mode != "LIVE") || (!live && intent.account_mode != "SIM") {
        return Some(reject(checks, "mode_universe", &intent.account_mode, &book.mode, "mode", None));
    }
    if !book.ramp_open {
        return Some(reject(checks, "mode_universe", "closed", "open", "ramp", None));
    }
    if !book.universe.iter().any(|item| item == &intent.instrument) {
        return Some(reject(checks, "mode_universe", &intent.instrument, "universe", "universe", None));
    }
    if book.require_protective_stop && intent.protective_stop.is_empty() {
        return Some(reject(checks, "mode_universe", "", "stop", "protective_stop", None));
    }
    push(checks, "mode_universe", &intent.instrument, &book.mode, true);
    None
}

fn rcb_gate(
    book: &KernelBook,
    intent: &Intent,
    checks: &mut Vec<Check>,
    size: &mut String,
) -> Option<(Decision, &'static str, String, Option<&'static str>)> {
    let Some(order) = decimal::parse(&intent.notional) else {
        return Some(reject(checks, "rcb", &intent.notional, &book.effective_limit, "malformed", None));
    };
    let Some(cap) = decimal::parse(&book.effective_limit) else {
        return Some(reject(checks, "rcb", &intent.notional, &book.effective_limit, "malformed", None));
    };
    if order > cap {
        if cap == 0 {
            return Some(reject(checks, "rcb", &intent.notional, &book.effective_limit, "rcb", None));
        }
        let Some(scaled) = decimal::mul_div(&intent.quantity, &book.effective_limit, &intent.notional) else {
            return Some(reject(checks, "rcb", &intent.notional, &book.effective_limit, "malformed", None));
        };
        if below_lot(book, &scaled) {
            return Some(reject(checks, "rcb", &scaled, &book.min_lot, "untradeable_at_this_capital", None));
        }
        *size = scaled;
    }
    push(checks, "rcb", &intent.notional, &book.effective_limit, true);
    None
}

fn drawdown_gate(
    book: &KernelBook,
    checks: &mut Vec<Check>,
) -> Option<(Decision, &'static str, String, Option<&'static str>)> {
    if cmp(&book.daily_loss, &book.daily_loss_limit) != Some(std::cmp::Ordering::Less) {
        return Some(reject(checks, "drawdown", &book.daily_loss, &book.daily_loss_limit, "drawdown", None));
    }
    if cmp(&book.drawdown, &book.drawdown_limit) != Some(std::cmp::Ordering::Less) {
        return Some(reject(checks, "drawdown", &book.drawdown, &book.drawdown_limit, "drawdown", None));
    }
    push(checks, "drawdown", &book.drawdown, &book.drawdown_limit, true);
    None
}

fn sizing_gate(
    book: &KernelBook,
    intent: &Intent,
    checks: &mut Vec<Check>,
    size: &mut String,
) -> Option<(Decision, &'static str, String, Option<&'static str>)> {
    let base = effective_quantity(intent, size);
    if !book.min_lot.is_empty()
        && cmp(&base, &book.min_lot) == Some(std::cmp::Ordering::Less)
        && book.min_lot_policy == MinLotPolicy::UseMinLot
    {
        *size = book.min_lot.clone();
        push(checks, "sizing", &base, &book.min_lot, true);
        return None;
    }
    if book.lot_step.is_empty() {
        return None;
    }
    let Some(floored) = floor_to_step(&base, &book.lot_step) else {
        return Some(reject(checks, "sizing", &base, &book.lot_step, "malformed", None));
    };
    if floored != base {
        if below_lot(book, &floored) {
            if book.min_lot_policy == MinLotPolicy::UseMinLot && !book.min_lot.is_empty() {
                *size = book.min_lot.clone();
                push(checks, "sizing", &base, &book.min_lot, true);
                return None;
            }
            return Some(reject(
                checks,
                "sizing",
                &floored,
                &book.min_lot,
                "untradeable_at_this_capital",
                None,
            ));
        }
        *size = floored;
    } else if !on_step(&base, &book.lot_step) {
        return Some(reject(checks, "sizing", &base, &book.lot_step, "malformed", None));
    }
    push(checks, "sizing", effective_quantity(intent, size).as_str(), &book.lot_step, true);
    None
}

fn risk_gate(
    book: &KernelBook,
    intent: &Intent,
    checks: &mut Vec<Check>,
    size: &str,
) -> Option<(Decision, &'static str, String, Option<&'static str>)> {
    let Some(base_pct) = mul_div(&book.max_risk_pct, &book.vol_scale, "1") else {
        return Some(reject(checks, "risk_budget", &book.max_risk_pct, "decimal", "malformed", None));
    };
    let Some(scaled_pct) = mul_div(&base_pct, &book.ramp_factor, "1") else {
        return Some(reject(checks, "risk_budget", &book.ramp_factor, "decimal", "malformed", None));
    };
    let Some(percent_budget) = percent_of(&book.equity, &scaled_pct) else {
        return Some(reject(checks, "risk_budget", &scaled_pct, "decimal", "malformed", None));
    };
    let budget = match kelly_cap(book, &percent_budget) {
        Ok(value) => value,
        Err(()) => return Some(reject(checks, "risk_budget", &book.kelly_ceiling, &percent_budget, "malformed", None)),
    };
    if cmp(&intent.risk_amount, &budget) == Some(std::cmp::Ordering::Greater) {
        return Some(reject(checks, "risk_budget", &intent.risk_amount, &budget, "risk_budget", None));
    }
    let quantity = effective_quantity(intent, size);
    if !book.min_lot.is_empty() && cmp(&quantity, &book.min_lot) == Some(std::cmp::Ordering::Less) {
        if book.min_lot_policy == MinLotPolicy::UseMinLot && !size.is_empty() {
            push(checks, "risk_budget", &quantity, &book.min_lot, true);
            return None;
        }
        if book.min_lot_policy == MinLotPolicy::UseMinLot {
            return Some(reject(
                checks,
                "risk_budget",
                &quantity,
                &book.min_lot,
                "untradeable_at_this_capital",
                None,
            ));
        }
        return Some(reject(
            checks,
            "risk_budget",
            &quantity,
            &book.min_lot,
            "untradeable_at_this_capital",
            None,
        ));
    }
    push(checks, "risk_budget", &intent.risk_amount, &budget, true);
    None
}

fn notional_gate(
    book: &KernelBook,
    intent: &Intent,
    checks: &mut Vec<Check>,
    size: &mut String,
) -> Option<(Decision, &'static str, String, Option<&'static str>)> {
    let Some(room) = notional_room(book) else {
        return Some(reject(checks, "notional_leverage", &book.open_notional, &book.max_notional_x, "malformed", None));
    };
    let Some(implied) = implied_notional(intent, size) else {
        return Some(reject(checks, "notional_leverage", &intent.notional, &room, "malformed", None));
    };
    let Some(order) = decimal::parse(&implied) else {
        return Some(reject(checks, "notional_leverage", &implied, &room, "malformed", None));
    };
    let Some(cap) = decimal::parse(&room) else {
        return Some(reject(checks, "notional_leverage", &implied, &room, "malformed", None));
    };
    if order > cap {
        if cap == 0 {
            return Some(reject(checks, "notional_leverage", &implied, &room, "notional", None));
        }
        let base = if size.is_empty() { intent.quantity.as_str() } else { size.as_str() };
        let Some(scaled) = decimal::mul_div(base, &room, &implied) else {
            return Some(reject(checks, "notional_leverage", &implied, &room, "malformed", None));
        };
        if below_lot(book, &scaled) {
            return Some(reject(checks, "notional_leverage", &scaled, &book.min_lot, "untradeable_at_this_capital", None));
        }
        *size = scaled;
    }
    if cmp(&book.leverage_used, &book.max_leverage) == Some(std::cmp::Ordering::Greater) {
        return Some(reject(checks, "notional_leverage", &book.leverage_used, &book.max_leverage, "leverage", None));
    }
    push(checks, "notional_leverage", &book.leverage_used, &book.max_leverage, true);
    None
}

fn concentration_gate(
    book: &KernelBook,
    checks: &mut Vec<Check>,
) -> Option<(Decision, &'static str, String, Option<&'static str>)> {
    if cmp(&book.concentration, &book.concentration_limit) != Some(std::cmp::Ordering::Less) {
        return Some(reject(
            checks,
            "concentration",
            &book.concentration,
            &book.concentration_limit,
            "concentration",
            None,
        ));
    }
    push(checks, "concentration", &book.concentration, &book.concentration_limit, true);
    None
}

fn margin_gate(
    book: &KernelBook,
    checks: &mut Vec<Check>,
) -> Option<(Decision, &'static str, String, Option<&'static str>)> {
    if cmp(&book.margin_level, &book.margin_floor) == Some(std::cmp::Ordering::Less) {
        return Some(reject(checks, "margin", &book.margin_level, &book.margin_floor, "margin", None));
    }
    push(checks, "margin", &book.margin_level, &book.margin_floor, true);
    None
}

/// Kelly is an upper reference. A higher Kelly figure never raises the constitution budget.
fn kelly_cap(book: &KernelBook, budget: &str) -> Result<String, ()> {
    if book.kelly_ceiling.is_empty() {
        return Ok(budget.to_string());
    }
    match cmp(&book.kelly_ceiling, budget) {
        Some(std::cmp::Ordering::Less) => Ok(book.kelly_ceiling.clone()),
        Some(_) => Ok(budget.to_string()),
        None => Err(()),
    }
}

fn cost_gate(
    book: &KernelBook,
    checks: &mut Vec<Check>,
) -> Option<(Decision, &'static str, String, Option<&'static str>)> {
    for value in [&book.spread, &book.commission, &book.swap, &book.modeled_slippage] {
        if decimal::parse(value).is_none() {
            return Some(reject(checks, "cost_model", value, "modeled", "cost_model", None));
        }
    }
    if book.wednesday_triple {
        let Some(triple) = mul_div(&book.swap, "3", "1") else {
            return Some(reject(checks, "cost_model", &book.swap, "3", "cost_model", None));
        };
        push(checks, "cost_model", &triple, "wednesday_triple", true);
        return None;
    }
    push(checks, "cost_model", &book.spread, "modeled", true);
    None
}

fn blackout_gate(
    book: &KernelBook,
    checks: &mut Vec<Check>,
) -> Option<(Decision, &'static str, String, Option<&'static str>)> {
    if book.news_blackout {
        return Some(reject(checks, "blackout_swap", "blackout", "", "blackout", None));
    }
    if book.swap_guard {
        return Some(reject(checks, "blackout_swap", "swap", "", "swap_guard", None));
    }
    push(checks, "blackout_swap", "clear", "", true);
    None
}

/// §9.1 sizes an L1 entry by one half. The rate-limit step still withholds a submit.
fn halve_for_l1(
    book: &KernelBook,
    intent: &Intent,
    checks: &mut Vec<Check>,
    size: &mut String,
) -> Option<(Decision, &'static str, String, Option<&'static str>)> {
    let base = if size.is_empty() { intent.quantity.as_str() } else { size.as_str() };
    let Some(halved) = decimal::mul_div(base, "1", "2") else {
        return Some(reject(checks, "halt_kill", base, "0.5", "malformed", None));
    };
    if below_lot(book, &halved) {
        return Some(reject(checks, "halt_kill", &halved, &book.min_lot, "untradeable_at_this_capital", None));
    }
    *size = halved;
    None
}

fn below_lot(book: &KernelBook, quantity: &str) -> bool {
    quantity == "0" || (!book.min_lot.is_empty() && cmp(quantity, &book.min_lot) == Some(std::cmp::Ordering::Less))
}

fn effective_quantity(intent: &Intent, size: &str) -> String {
    if size.is_empty() {
        intent.quantity.clone()
    } else {
        size.to_string()
    }
}

fn implied_notional(intent: &Intent, size: &str) -> Option<String> {
    if size.is_empty() {
        Some(intent.notional.clone())
    } else {
        decimal::mul_div(&intent.notional, size, &intent.quantity)
    }
}

fn notional_room(book: &KernelBook) -> Option<String> {
    let cap = decimal::mul_div(&book.equity, &book.max_notional_x, "1")?;
    let cap_value = decimal::parse(&cap)?;
    let open = decimal::parse(&book.open_notional)?;
    if open >= cap_value {
        Some("0".to_string())
    } else {
        Some(decimal::format(cap_value - open))
    }
}

fn is_blocking_halt(book: &KernelBook) -> bool {
    matches!(book.halt_level.as_str(), "L2" | "L3" | "L4") || matches!(book.kill_state.as_str(), "K1" | "K2")
}

fn reject(
    checks: &mut Vec<Check>,
    name: &'static str,
    value: &str,
    limit: &str,
    reason: &'static str,
    arm_halt: Option<&'static str>,
) -> (Decision, &'static str, String, Option<&'static str>) {
    push(checks, name, value, limit, false);
    (Decision::Reject, reason, String::new(), arm_halt)
}

fn push(checks: &mut Vec<Check>, name: &'static str, value: &str, limit: &str, passed: bool) {
    checks.push(Check { name, value: value.to_string(), limit: limit.to_string(), passed });
}
