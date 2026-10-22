use std::time::{SystemTime, UNIX_EPOCH};

use crate::{
    Decision, Intent, KernelBook, PollHook, Session, decide, POLL_INTERVAL_SECS, STAGING_SECS,
};

fn book() -> KernelBook {
    KernelBook {
        mode: "SIM".to_string(),
        universe: vec!["EURUSD".to_string()],
        halt_level: String::new(),
        kill_state: String::new(),
        fingerprint: "fp-1".to_string(),
        rcb_version: 1,
        constitution_version: 1,
        constitution_pin: 1,
        effective_limit: "1000".to_string(),
        equity: "1000".to_string(),
        daily_loss: "0".to_string(),
        daily_loss_limit: "20".to_string(),
        drawdown: "0".to_string(),
        drawdown_limit: "100".to_string(),
        max_risk_pct: "0.5".to_string(),
        max_notional_x: "3".to_string(),
        open_notional: "0".to_string(),
        leverage_used: "1".to_string(),
        max_leverage: "10".to_string(),
        concentration: "0.1".to_string(),
        concentration_limit: "0.5".to_string(),
        margin_level: "400".to_string(),
        margin_floor: "150".to_string(),
        news_blackout: false,
        swap_guard: false,
        rate_limited: false,
        require_protective_stop: true,
        min_lot: String::new(),
        ramp_open: true,
        safe_mode: false,
        market_stale: false,
    }
}

fn intent() -> Intent {
    Intent {
        intent_id: "i-1".to_string(),
        group: "A".to_string(),
        account_mode: "SIM".to_string(),
        instrument: "EURUSD".to_string(),
        quantity: "1".to_string(),
        notional: "100".to_string(),
        risk_amount: "4".to_string(),
        protective_stop: "1.08".to_string(),
        fingerprint: "fp-1".to_string(),
        reduce_only: false,
    }
}

#[test]
fn an_entry_inside_the_loaded_limits_is_allowed() {
    let verdict = decide(&book(), &intent(), "2026-10-22T21:00:00Z");
    assert_eq!(verdict.decision, Decision::Allow);
    assert!(verdict.reason.is_empty());
    assert_eq!(verdict.kernel_version, "0.1.0");
    assert!(verdict.checks.iter().all(|check| check.passed));
    let names: Vec<_> = verdict.checks.iter().map(|check| check.name).collect();
    assert_eq!(
        names,
        vec![
            "halt_kill",
            "fingerprint",
            "mode_universe",
            "rcb",
            "drawdown",
            "risk_budget",
            "notional_leverage",
            "concentration",
            "margin",
            "blackout_swap",
            "rate_limit",
        ]
    );
    assert!(!verdict.persisted);
}

#[test]
fn halt_is_the_first_check_and_a_flatten_still_passes() {
    let mut state = book();
    state.halt_level = "L2".to_string();
    let blocked = decide(&state, &intent(), "2026-10-22T21:00:00Z");
    assert_eq!(blocked.decision, Decision::Reject);
    assert_eq!(blocked.reason, "halt");
    assert_eq!(blocked.checks.len(), 1);
    assert!(!blocked.checks[0].passed);
    let mut flatten = intent();
    flatten.reduce_only = true;
    let allowed = decide(&state, &flatten, "2026-10-22T21:00:00Z");
    assert_eq!(allowed.decision, Decision::Allow);
    assert_eq!(allowed.checks[0].name, "halt_kill");
}

#[test]
fn kill_blocks_before_a_later_risk_check() {
    let mut state = book();
    state.kill_state = "K3".to_string();
    state.halt_level = "L2".to_string();
    let mut flatten = intent();
    flatten.reduce_only = true;
    let verdict = decide(&state, &flatten, "2026-10-22T21:00:00Z");
    assert_eq!(verdict.reason, "kill");
    assert_eq!(verdict.checks.len(), 1);
}

#[test]
fn ts05_rejects_cover_risk_notional_concentration_margin_blackout_swap_and_universe() {
    let issued = "2026-10-22T21:00:00Z";
    let mut risk = book();
    let mut big = intent();
    big.risk_amount = "9".to_string();
    assert_eq!(decide(&risk, &big, issued).reason, "risk_budget");
    risk.max_notional_x = "0".to_string();
    let mut oversized = intent();
    oversized.notional = "10".to_string();
    assert_eq!(decide(&risk, &oversized, issued).reason, "notional");
    let mut crowded = book();
    crowded.concentration = "0.5".to_string();
    assert_eq!(decide(&crowded, &intent(), issued).reason, "concentration");
    let mut thin = book();
    thin.margin_level = "100".to_string();
    assert_eq!(decide(&thin, &intent(), issued).reason, "margin");
    let mut blackout = book();
    blackout.news_blackout = true;
    assert_eq!(decide(&blackout, &intent(), issued).reason, "blackout");
    let mut swap = book();
    swap.swap_guard = true;
    assert_eq!(decide(&swap, &intent(), issued).reason, "swap_guard");
    let mut unknown = intent();
    unknown.instrument = "GBPUSD".to_string();
    assert_eq!(decide(&book(), &unknown, issued).reason, "universe");
    let mut live2 = book();
    live2.mode = "LIVE-L2".to_string();
    live2.universe = vec!["EURUSD".to_string()];
    let mut live_intent = intent();
    live_intent.account_mode = "LIVE".to_string();
    assert_eq!(decide(&live2, &live_intent, issued).reason, "a_dec_02");
}

#[test]
fn ts06_sizes_down_to_the_ratified_limit() {
    let mut state = book();
    state.effective_limit = "50".to_string();
    let mut order = intent();
    order.notional = "100".to_string();
    order.quantity = "2".to_string();
    let verdict = decide(&state, &order, "2026-10-22T21:00:00Z");
    assert_eq!(verdict.decision, Decision::AllowWithSize);
    assert_eq!(verdict.size, "1");
    assert!(verdict.decision.allows_broker_submit());
}

#[test]
fn ts09_swap_guard_rejects_the_entry() {
    let mut state = book();
    state.swap_guard = true;
    let verdict = decide(&state, &intent(), "2026-10-22T21:00:00Z");
    assert_eq!(verdict.decision, Decision::Reject);
    assert_eq!(verdict.reason, "swap_guard");
    assert_eq!(verdict.checks.last().unwrap().name, "blackout_swap");
}

#[test]
fn a_missing_protective_stop_does_not_open() {
    let mut order = intent();
    order.protective_stop.clear();
    assert_eq!(decide(&book(), &order, "2026-10-22T21:00:00Z").reason, "protective_stop");
}

#[test]
fn the_wrong_fingerprint_arms_l2_and_the_file_restores_it() {
    let mut order = intent();
    order.fingerprint = "other".to_string();
    let verdict = decide(&book(), &order, "2026-10-22T21:00:00Z");
    assert_eq!(verdict.reason, "fingerprint");
    assert_eq!(verdict.arm_halt, Some("L2"));
    let dir = std::env::temp_dir().join(format!("sate-halt-{}", unique()));
    std::fs::create_dir_all(&dir).unwrap();
    let path = dir.join("halt");
    let mut session = Session::open(book(), 1_700_000_000);
    let stored = session.handle(&order, "2026-10-22T21:00:00Z");
    assert_eq!(session.book.halt_level, "L2");
    session.save_halt(&path).unwrap();
    session.book.halt_level.clear();
    session.load_halt(&path).unwrap();
    assert_eq!(session.book.halt_level, "L2");
    assert_eq!(stored.reason, "fingerprint");
    let _ = std::fs::remove_dir_all(&dir);
}

#[test]
fn a_poll_failure_enters_safe_mode_and_blocks_the_next_entry() {
    let mut session = Session::open(book(), 1_000);
    assert_eq!(POLL_INTERVAL_SECS, 5);
    session.on_poll(1_000, false);
    assert!(session.book.safe_mode);
    assert_eq!(session.poll.next_due, 1_005);
    let verdict = session.handle(&intent(), "2026-10-22T21:00:00Z");
    assert_eq!(verdict.reason, "safe_mode");
    session.on_poll(1_005, true);
    assert!(!session.book.safe_mode);
    let hook = PollHook::new(10);
    assert_eq!(hook.next_due, 15);
}

#[test]
fn duplicate_intent_does_not_submit_twice_and_reject_never_submits() {
    let mut session = Session::open(book(), 50);
    let first = session.handle(&intent(), "2026-10-22T21:00:00Z");
    assert!(session.submit_persisted(&first).is_err());
    let mut recorded = first.clone();
    recorded.persisted = true;
    session.submit_persisted(&recorded).unwrap();
    let second = session.handle(&intent(), "2026-10-22T21:00:01Z");
    assert_eq!(second.decision, Decision::Allow);
    assert_eq!(session.adapter.submits.len(), 1);
    assert_eq!(session.verdict_count(), 1);
    let mut rejected = intent();
    rejected.intent_id = "i-2".to_string();
    rejected.protective_stop.clear();
    let denial = session.handle(&rejected, "2026-10-22T21:00:02Z");
    let mut persisted_denial = denial.clone();
    persisted_denial.persisted = true;
    assert!(session.submit_persisted(&persisted_denial).is_err());
    assert_eq!(session.adapter.submits.len(), 1);
    assert_eq!(session.intents, session.verdict_count());
}

#[test]
fn a_fresh_session_does_not_claim_the_24h_gate() {
    let mut session = Session::open(book(), 1_000);
    session.handle(&intent(), "2026-10-22T21:00:00Z");
    assert!(!session.gate_met(1_001));
    assert!(session.gate_met(1_000 + STAGING_SECS));
    assert!(!Session::open(book(), 1_000).gate_met(1_000 + STAGING_SECS));
}

#[test]
fn rcb_is_checked_before_drawdown() {
    let mut state = book();
    state.effective_limit = "0".to_string();
    state.daily_loss = "20".to_string();
    let verdict = decide(&state, &intent(), "2026-10-22T21:00:00Z");
    assert_eq!(verdict.reason, "rcb");
    assert_eq!(verdict.checks.last().unwrap().name, "rcb");
    assert!(verdict.checks.iter().all(|check| check.name != "drawdown"));
}

#[test]
fn stale_market_data_blocks_an_entry_and_still_allows_a_flatten() {
    let mut state = book();
    state.market_stale = true;
    assert_eq!(decide(&state, &intent(), "2026-10-22T21:00:00Z").reason, "stale");
    let mut flatten = intent();
    flatten.reduce_only = true;
    assert_eq!(decide(&state, &flatten, "2026-10-22T21:00:00Z").decision, Decision::Allow);
}

#[test]
fn the_wrong_account_mode_is_rejected() {
    let mut order = intent();
    order.account_mode = "LIVE".to_string();
    let verdict = decide(&book(), &order, "2026-10-22T21:00:00Z");
    assert_eq!(verdict.decision, Decision::Reject);
    assert_eq!(verdict.reason, "mode");
}

#[test]
fn a_drifted_constitution_pin_rejects_before_the_halt_check() {
    let mut state = book();
    state.constitution_pin = 2;
    state.halt_level = "L2".to_string();
    let verdict = decide(&state, &intent(), "2026-10-22T21:00:00Z");
    assert_eq!(verdict.reason, "constitution");
    assert_eq!(verdict.checks.len(), 1);
}

#[test]
fn l1_halves_the_size_and_a_rate_limit_still_throttles() {
    let mut state = book();
    state.halt_level = "L1".to_string();
    let halved = decide(&state, &intent(), "2026-10-22T21:00:00Z");
    assert_eq!(halved.decision, Decision::AllowWithSize);
    assert_eq!(halved.size, "0.5");
    state.rate_limited = true;
    let throttled = decide(&state, &intent(), "2026-10-22T21:00:00Z");
    assert_eq!(throttled.decision, Decision::Throttle);
    assert_eq!(throttled.reason, "rate_limit");
    assert!(!throttled.decision.allows_broker_submit());
}

#[test]
fn k1_blocks_an_entry_and_still_allows_a_flatten() {
    let mut state = book();
    state.kill_state = "K1".to_string();
    assert_eq!(decide(&state, &intent(), "2026-10-22T21:00:00Z").reason, "kill");
    let mut flatten = intent();
    flatten.reduce_only = true;
    assert_eq!(decide(&state, &flatten, "2026-10-22T21:00:00Z").decision, Decision::Allow);
}

#[test]
fn resume_restores_halt_without_replacing_the_loaded_mode() {
    let dir = std::env::temp_dir().join(format!("sate-resume-{}", unique()));
    std::fs::create_dir_all(&dir).unwrap();
    let path = dir.join("halt");
    let mut saved = book();
    saved.mode = "LIVE-L2".to_string();
    saved.halt_level = "L2".to_string();
    crate::halt::save(&path, &saved).unwrap();
    let mut loaded = book();
    loaded.mode = "SIM".to_string();
    let session = Session::resume(loaded, &path, 10).unwrap();
    assert_eq!(session.book.mode, "SIM");
    assert_eq!(session.book.halt_level, "L2");
    assert!(!session.gate_met(10 + STAGING_SECS));
    let missing = dir.join("absent");
    let clear = Session::resume(book(), &missing, 10).unwrap();
    assert!(clear.book.halt_level.is_empty());
    std::fs::write(&path, "nope\n").unwrap();
    assert!(Session::resume(book(), &path, 10).is_err());
    let _ = std::fs::remove_dir_all(&dir);
}

#[test]
fn latency_is_recorded_without_claiming_the_p99_target() {
    let verdict = decide(&book(), &intent(), "2026-10-22T21:00:00Z");
    let _baseline_us = verdict.latency_us;
    assert!(verdict.issued_at.ends_with('Z'));
}

fn unique() -> u128 {
    SystemTime::now().duration_since(UNIX_EPOCH).map(|item| item.as_nanos()).unwrap_or(0)
}
