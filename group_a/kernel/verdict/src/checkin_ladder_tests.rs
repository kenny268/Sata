use crate::{
    checkin_tier, decide, record_checkin, set_checkin_away, CheckinBook, CheckinChannel, CheckinTier, Decision,
    Intent, KernelBook, MinLotPolicy, Session, SlippageWindow,
};

fn live_book(days: u64) -> KernelBook {
    KernelBook {
        mode: "LIVE-L1".to_string(),
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
        checkin: CheckinBook {
            last_day: 0,
            current_day: days,
            ..CheckinBook::default()
        },
    }
}

fn live_intent(id: &str, reduce_only: bool) -> Intent {
    Intent {
        intent_id: id.to_string(),
        group: "A".to_string(),
        account_mode: "LIVE".to_string(),
        instrument: "EURUSD".to_string(),
        quantity: "1".to_string(),
        notional: "100".to_string(),
        risk_amount: "4".to_string(),
        protective_stop: "1.08".to_string(),
        fingerprint: "fp-1".to_string(),
        reduce_only,
        abstain: false,
    }
}

#[test]
fn day10_blocks_live_new_risk_and_day14_blocks_even_with_manage_mode() {
    let state = live_book(10);
    assert_eq!(checkin_tier(&state.checkin), CheckinTier::ManageOnly);
    let blocked = decide(&state, &live_intent("i-10", false), "2026-10-22T21:00:00Z");
    assert_eq!(blocked.decision, Decision::Reject);
    assert_eq!(blocked.reason, "checkin");

    let state = live_book(14);
    assert_eq!(checkin_tier(&state.checkin), CheckinTier::Flatten);
    let flatten = decide(&state, &live_intent("i-14-flat", true), "2026-10-22T21:00:01Z");
    assert_eq!(flatten.decision, Decision::Allow);
    let blocked = decide(&state, &live_intent("i-14-new", false), "2026-10-22T21:00:02Z");
    assert_eq!(blocked.reason, "checkin_flatten");
}

#[test]
fn sim_continues_during_lapse_op05() {
    let mut state = live_book(14);
    state.mode = "SIM".to_string();
    let sim = Intent {
        intent_id: "i-sim".to_string(),
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
    };
    let allowed = decide(&state, &sim, "2026-10-22T21:00:00Z");
    assert_eq!(allowed.decision, Decision::Allow);
}

#[test]
fn session_records_checkin_and_away_in_kernel() {
    let mut session = Session::open(live_book(9), 1);
    session.book.checkin.current_day = 9;
    record_checkin(&mut session.book.checkin, CheckinChannel::TelegramAlive);
    assert_eq!(session.book.checkin.last_day, 9);
    set_checkin_away(&mut session.book.checkin, 5).unwrap();
    assert_eq!(session.book.checkin.away_until_day, 14);
}
