use crate::{apply_kill, decide, escalate, mode_transition, Decision, HaltLevel, HaltTrigger, Intent, KernelBook, KillLevel, MinLotPolicy, ModeEvent, Session, SlippageWindow};

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
        ramp_open: true,
        safe_mode: false,
        market_stale: false,
        trading_revoked: false,
        checkin: Default::default(),
    }
}

fn intent() -> Intent {
    intent_with_id("i-1")
}

fn intent_with_id(intent_id: &str) -> Intent {
    Intent {
        intent_id: intent_id.to_string(),
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
fn oc04_all_halt_stays_partial_when_b_is_absent() {
    let mut state = book();
    state.trading_revoked = true;
    let mut flatten = intent_with_id("i-flat");
    flatten.reduce_only = true;
    assert_eq!(decide(&state, &flatten, "2026-10-22T21:00:00Z").reason, "revoked");
}

#[test]
fn three_kill_levels_are_exercised_in_sim() {
    let mut session = Session::open(book(), 1);
    let (k1, _) = apply_kill(&session.book.kill_state, KillLevel::K1).unwrap();
    session.book.kill_state = k1;
    assert_eq!(session.handle(&intent_with_id("i-k1"), "2026-10-22T21:00:00Z").reason, "kill");
    session.book.kill_state.clear();
    let (k2, _) = apply_kill("", KillLevel::K2).unwrap();
    session.book.kill_state = k2;
    assert_eq!(session.handle(&intent_with_id("i-k2"), "2026-10-22T21:00:01Z").reason, "kill");
    let (k3, revoke) = apply_kill("", KillLevel::K3).unwrap();
    session.book.kill_state = k3;
    session.book.trading_revoked = revoke;
    assert_eq!(session.handle(&intent_with_id("i-k3"), "2026-10-22T21:00:02Z").reason, "revoked");
}

#[test]
fn mode_transition_to_manage_only_is_auditable() {
    let next = mode_transition("LIVE-L1", ModeEvent::LiveToSim).unwrap();
    assert_eq!(next, "MANAGE_ONLY");
    let mut session = Session::open(book(), 1);
    session.book.mode = "LIVE-L1".to_string();
    session.book.mode = mode_transition(&session.book.mode, ModeEvent::LiveToSim).unwrap().to_string();
    assert_eq!(session.book.mode, "MANAGE_ONLY");
}

#[test]
fn ladder_escalates_to_l4_on_ops_heartbeat() {
    let level = escalate(HaltLevel::L2, HaltTrigger::OpsHeartbeat);
    assert_eq!(level, HaltLevel::L4);
}

#[test]
fn k1_still_allows_a_flatten() {
    let mut state = book();
    state.kill_state = "K1".to_string();
    let mut flatten = intent();
    flatten.reduce_only = true;
    assert_eq!(decide(&state, &flatten, "2026-10-22T21:00:00Z").decision, Decision::Allow);
}
