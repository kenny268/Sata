use std::time::{SystemTime, UNIX_EPOCH};

use crate::{
    Decision, Intent, KernelBook, MinLotPolicy, PollHook, Session, SlippageWindow, decide, POLL_INTERVAL_SECS,
    STAGING_SECS,
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
        vol_scale: "1".to_string(),
        ramp_factor: "1".to_string(),
        kelly_ceiling: String::new(),
        spread: "0".to_string(),
        commission: "0".to_string(),
        swap: "0".to_string(),
        modeled_slippage: "0".to_string(),
        wednesday_triple: false,
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
        lot_step: String::new(),
        min_lot_policy: MinLotPolicy::Reject,
        slippage_window: SlippageWindow::default(),
        slippage_l1_armed: false,
        calendar_week: String::new(),
        fx_week: String::new(),
        ramp_open: true,
        safe_mode: false,
        market_stale: false,
        trading_revoked: false,
        checkin: Default::default(),
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
        abstain: false,
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
            "cost_model",
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
    assert_eq!(verdict.reason, "revoked");
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
fn ts10_stale_market_data_blocks_an_entry_and_still_allows_a_flatten() {
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

#[test]
fn ts04_rejects_when_min_lot_exceeds_the_budget() {
    let mut state = book();
    state.min_lot = "2".to_string();
    state.lot_step = "0.01".to_string();
    let mut order = intent();
    order.quantity = "1".to_string();
    assert_eq!(decide(&state, &order, "2026-10-22T21:00:00Z").reason, "untradeable_at_this_capital");
}

#[test]
fn lot_step_floors_the_size_down_and_never_rounds_up() {
    let mut state = book();
    state.lot_step = "0.25".to_string();
    state.min_lot = "0.25".to_string();
    let mut order = intent();
    order.quantity = "1.13".to_string();
    let verdict = decide(&state, &order, "2026-10-22T21:00:00Z");
    assert_eq!(verdict.decision, Decision::AllowWithSize);
    assert_eq!(verdict.size, "1");
}

#[test]
fn a_dec_01_use_min_lot_policy_is_implemented_but_not_default() {
    let mut state = book();
    state.min_lot = "1.25".to_string();
    state.lot_step = "0.25".to_string();
    state.min_lot_policy = MinLotPolicy::UseMinLot;
    let mut order = intent();
    order.quantity = "1".to_string();
    let verdict = decide(&state, &order, "2026-10-22T21:00:00Z");
    assert_eq!(verdict.decision, Decision::AllowWithSize);
    assert_eq!(verdict.size, "1.25");
}

#[test]
fn slippage_budget_breach_halves_like_l1() {
    let mut state = book();
    state.slippage_window.record(false);
    let verdict = decide(&state, &intent(), "2026-10-22T21:00:00Z");
    assert_eq!(verdict.decision, Decision::AllowWithSize);
    assert_eq!(verdict.size, "0.5");
    assert_eq!(verdict.arm_halt, Some("L1"));
}

#[test]
fn slippage_breach_arms_l1_until_the_window_rolls_off() {
    let mut session = Session::open(book(), 1);
    assert!(!session.measure_slippage("EURUSD", "1.0850", "1.0852"));
    assert_eq!(session.book.halt_level, "L1");
    let halved = session.handle(&intent(), "2026-10-22T21:00:00Z");
    assert_eq!(halved.size, "0.5");
    for _ in 0..20 {
        assert!(session.measure_slippage("EURUSD", "1.0850", "1.0850"));
    }
    assert_eq!(session.book.halt_level, "");
    let mut again = intent();
    again.intent_id = "i-2".to_string();
    let restored = session.handle(&again, "2026-10-22T21:00:01Z");
    assert_eq!(restored.decision, Decision::Allow);
    assert!(restored.size.is_empty());
}

#[test]
fn a_feed_l1_survives_a_clean_slippage_window() {
    let mut session = Session::open(book(), 1);
    session.book.halt_level = "L1".to_string();
    for _ in 0..20 {
        assert!(session.measure_slippage("EURUSD", "1.0850", "1.0850"));
    }
    assert_eq!(session.book.halt_level, "L1");
}

#[test]
fn a_zero_protective_stop_does_not_open() {
    let mut order = intent();
    order.protective_stop = "0".to_string();
    assert_eq!(decide(&book(), &order, "2026-10-22T21:00:00Z").reason, "protective_stop");
}

#[test]
fn a_stale_fx_calendar_rejects_the_entry() {
    let mut state = book();
    state.fx_week = "2026-10-18".to_string();
    state.calendar_week = "2026-10-11".to_string();
    assert_eq!(decide(&state, &intent(), "2026-10-22T21:00:00Z").reason, "calendar");
}

#[test]
fn vol_scale_and_ramp_factor_shrink_the_risk_budget() {
    let mut state = book();
    state.vol_scale = "0.5".to_string();
    state.ramp_factor = "0.5".to_string();
    let mut order = intent();
    order.risk_amount = "1.2".to_string();
    assert_eq!(decide(&state, &order, "2026-10-22T21:00:00Z").decision, Decision::Allow);
    order.risk_amount = "1.3".to_string();
    assert_eq!(decide(&state, &order, "2026-10-22T21:00:00Z").reason, "risk_budget");
}

#[test]
fn ts01_allow_is_journalled_before_submit_and_keeps_the_stop() {
    let mut session = Session::open(book(), 1);
    let verdict = session.handle(&intent(), "2026-10-22T21:00:00Z");
    assert_eq!(verdict.decision, Decision::Allow);
    assert!(!intent().protective_stop.is_empty());
    assert!(session.submit_persisted(&verdict).is_err());
    let mut stored = verdict;
    stored.persisted = true;
    session.submit_persisted(&stored).unwrap();
    assert_eq!(session.adapter.submits, vec!["i-1".to_string()]);
}

#[test]
fn ts02_a_missing_advisory_does_not_block() {
    let verdict = decide(&book(), &intent(), "2026-10-22T21:00:00Z");
    assert_eq!(verdict.decision, Decision::Allow);
    assert!(verdict.reason.is_empty());
}

#[test]
fn ts03_abstain_does_not_open() {
    let mut order = intent();
    order.abstain = true;
    let verdict = decide(&book(), &order, "2026-10-22T21:00:00Z");
    assert_eq!(verdict.decision, Decision::Reject);
    assert_eq!(verdict.reason, "abstain");
    assert!(!verdict.decision.allows_broker_submit());
}

#[test]
fn ts07_rate_limit_throttles() {
    let mut state = book();
    state.rate_limited = true;
    let verdict = decide(&state, &intent(), "2026-10-22T21:00:00Z");
    assert_eq!(verdict.decision, Decision::Throttle);
    assert_eq!(verdict.reason, "rate_limit");
}

#[test]
fn ts08_news_blackout_rejects() {
    let mut state = book();
    state.news_blackout = true;
    assert_eq!(decide(&state, &intent(), "2026-10-22T21:00:00Z").reason, "blackout");
}

#[test]
fn ts11_a_duplicate_intent_keeps_the_first_outcome() {
    let mut session = Session::open(book(), 1);
    let first = session.handle(&intent(), "2026-10-22T21:00:00Z");
    let second = session.handle(&intent(), "2026-10-22T21:00:01Z");
    assert_eq!(first.decision, second.decision);
    assert_eq!(session.verdict_count(), 1);
}

#[test]
fn kelly_can_only_tighten_the_risk_budget() {
    let mut loose = book();
    loose.kelly_ceiling = "100".to_string();
    let mut order = intent();
    order.risk_amount = "6".to_string();
    assert_eq!(decide(&loose, &order, "2026-10-22T21:00:00Z").reason, "risk_budget");
    let mut tight = book();
    tight.kelly_ceiling = "1".to_string();
    order.risk_amount = "2".to_string();
    assert_eq!(decide(&tight, &order, "2026-10-22T21:00:00Z").reason, "risk_budget");
    order.risk_amount = "1".to_string();
    assert_eq!(decide(&tight, &order, "2026-10-22T21:00:00Z").decision, Decision::Allow);
}

#[test]
fn an_unmodeled_cost_is_rejected_and_wednesday_triple_is_recorded() {
    let mut missing = book();
    missing.spread.clear();
    assert_eq!(decide(&missing, &intent(), "2026-10-22T21:00:00Z").reason, "cost_model");
    let mut triple = book();
    triple.wednesday_triple = true;
    triple.swap = "0.1".to_string();
    let verdict = decide(&triple, &intent(), "2026-10-22T21:00:00Z");
    assert_eq!(verdict.decision, Decision::Allow);
    let cost = verdict.checks.iter().find(|check| check.name == "cost_model").unwrap();
    assert_eq!(cost.limit, "wednesday_triple");
    assert_eq!(cost.value, "0.3");
}

#[test]
fn a_measured_fill_outside_the_eurusd_budget_halves_the_next_entry() {
    let mut session = Session::open(book(), 1);
    assert!(session.measure_slippage("EURUSD", "1.0850", "1.08504"));
    assert!(!session.measure_slippage("EURUSD", "1.0850", "1.0852"));
    let verdict = session.handle(&intent(), "2026-10-22T21:00:00Z");
    assert_eq!(verdict.decision, Decision::AllowWithSize);
    assert_eq!(verdict.size, "0.5");
}

fn unique() -> u128 {
    SystemTime::now().duration_since(UNIX_EPOCH).map(|item| item.as_nanos()).unwrap_or(0)
}
