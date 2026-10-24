use sate_a_verdict::{Decision, Verdict};

use super::{
    accept_verdict, Ack, Book, BrokerPort, BrokerView, OmsError, Order, OrderState, PortError,
    Submission, SubmitRequest,
};

struct Fake {
    submits: Vec<String>,
    cancels: u32,
    queries: u32,
    submit_script: Vec<Result<Ack, PortError>>,
    query_script: Vec<Result<BrokerView, PortError>>,
    cancel_script: Vec<Result<Ack, PortError>>,
}

impl Fake {
    fn new() -> Self {
        Self {
            submits: Vec::new(),
            cancels: 0,
            queries: 0,
            submit_script: Vec::new(),
            query_script: Vec::new(),
            cancel_script: Vec::new(),
        }
    }
}

impl BrokerPort for Fake {
    fn submit(&mut self, request: &SubmitRequest) -> Result<Ack, PortError> {
        self.submits.push(request.correlation_id.clone());
        pop(&mut self.submit_script)
    }

    fn cancel(&mut self, _correlation_id: &str) -> Result<Ack, PortError> {
        self.cancels += 1;
        pop(&mut self.cancel_script)
    }

    fn query(&mut self, _correlation_id: &str) -> Result<BrokerView, PortError> {
        self.queries += 1;
        pop(&mut self.query_script)
    }
}

fn pop<T>(script: &mut Vec<Result<T, PortError>>) -> Result<T, PortError> {
    if script.is_empty() {
        Err(PortError::Timeout)
    } else {
        script.remove(0)
    }
}

fn ack(broker_id: Option<&str>) -> Result<Ack, PortError> {
    Ok(Ack {
        broker_id: broker_id.map(str::to_string),
    })
}

fn verdict(intent_id: &str, decision: Decision, size: &str, persisted: bool) -> Verdict {
    Verdict {
        intent_id: intent_id.to_string(),
        kernel_version: "0.1.0".to_string(),
        decision,
        reason: "",
        size: size.to_string(),
        checks: Vec::new(),
        constitution_version: 1,
        rcb_version: 1,
        halt_level: String::new(),
        kill_state: String::new(),
        latency_us: 1,
        issued_at: "2026-10-22T21:00:00Z".to_string(),
        arm_halt: None,
        persisted,
    }
}

fn request(intent_id: &str) -> Submission {
    Submission {
        intent_id: intent_id.to_string(),
        group: "A".to_string(),
        instrument: "EURUSD".to_string(),
        side: "BUY".to_string(),
        quantity: "1".to_string(),
        protective_stop: "1.08".to_string(),
        reduce_only: false,
    }
}

#[test]
fn reject_and_throttle_do_not_submit() {
    assert!(accept_verdict(Decision::Allow).is_ok());
    assert!(accept_verdict(Decision::AllowWithSize).is_ok());
    assert!(accept_verdict(Decision::Reject).is_err());
    assert!(accept_verdict(Decision::Throttle).is_err());
}

#[test]
fn an_allow_verdict_submits_once_and_a_duplicate_returns_it() {
    let mut book = Book::default();
    let mut broker = Fake::new();
    broker.submit_script.push(ack(None));
    let approved = verdict("i-1", Decision::Allow, "", true);
    let order = book.submit(&approved, &request("i-1"), &mut broker).unwrap();
    assert_eq!(order.state, OrderState::Submitted);
    assert_eq!(order.client_id, "i-1");
    assert_eq!(order.correlation_id, "A:i-1");
    assert_eq!(order.broker_id, None);
    assert_eq!(order.remainder, "1");
    let again = book.submit(&approved, &request("i-1"), &mut broker).unwrap();
    assert_eq!(again, order);
    let mut resized = request("i-1");
    resized.quantity = "2".to_string();
    let kept = book.submit(&approved, &resized, &mut broker).unwrap();
    assert_eq!(kept.quantity, "1");
    assert_eq!(broker.submits, vec!["A:i-1".to_string()]);
    assert_eq!(book.events()[0].kind, "submit");
}

#[test]
fn throttle_reject_and_an_unpersisted_verdict_do_not_reach_the_broker() {
    let mut book = Book::default();
    let mut broker = Fake::new();
    broker.submit_script.push(ack(None));
    let throttle = verdict("i-1", Decision::Throttle, "", true);
    assert_eq!(book.submit(&throttle, &request("i-1"), &mut broker), Err(OmsError::Verdict));
    let reject = verdict("i-1", Decision::Reject, "", true);
    assert_eq!(book.submit(&reject, &request("i-1"), &mut broker), Err(OmsError::Verdict));
    let fresh = verdict("i-1", Decision::Allow, "", false);
    assert_eq!(book.submit(&fresh, &request("i-1"), &mut broker), Err(OmsError::Verdict));
    assert!(broker.submits.is_empty());
}

#[test]
fn a_timeout_stays_one_broker_order_until_the_broker_is_queried() {
    let mut book = Book::default();
    let mut broker = Fake::new();
    let approved = verdict("i-1", Decision::Allow, "", true);
    let order = book.submit(&approved, &request("i-1"), &mut broker).unwrap();
    assert!(order.uncertain);
    assert_eq!(order.state, OrderState::New);
    assert_eq!(book.dead_letter()[0].reason, "timeout");
    assert_eq!(book.manual_reconciliation()[0].reason, "timeout");
    let duplicate = book.submit(&approved, &request("i-1"), &mut broker).unwrap();
    assert_eq!(duplicate.correlation_id, order.correlation_id);
    assert_eq!(book.retry("i-1", &mut broker), Err(OmsError::Recon));
    assert_eq!(broker.queries, 0);
    book.note_recon(true);
    for _ in 0..5 {
        assert_eq!(book.retry("i-1", &mut broker), Err(OmsError::AwaitingBroker));
        book.submit(&approved, &request("i-1"), &mut broker).unwrap();
    }
    assert_eq!(broker.submits, vec!["A:i-1".to_string()]);
    broker.query_script.push(Ok(BrokerView::Absent));
    broker.submit_script.push(ack(Some("T-100")));
    let resumed = book.retry("i-1", &mut broker).unwrap();
    assert_eq!(resumed.state, OrderState::Submitted);
    assert_eq!(resumed.broker_id.as_deref(), Some("T-100"));
    assert!(!resumed.uncertain);
    assert!(book.dead_letter().is_empty());
    assert_eq!(broker.submits, vec!["A:i-1".to_string(), "A:i-1".to_string()]);
}

#[test]
fn a_partial_fill_stays_on_the_same_order() {
    let mut book = Book::default();
    let mut broker = Fake::new();
    broker.submit_script.push(ack(None));
    let approved = verdict("i-1", Decision::Allow, "", true);
    book.submit(&approved, &request("i-1"), &mut broker).unwrap();
    let partial = book.apply_fill("i-1", "f-1", "0.4", "2026-10-22T21:00:01Z").unwrap();
    assert_eq!(partial.state, OrderState::Partial);
    assert_eq!(partial.filled, "0.4");
    assert_eq!(partial.remainder, "0.6");
    assert_eq!(book.events().last().unwrap().kind, "partial");
    let repeated = book.apply_fill("i-1", "f-1", "0.4", "2026-10-22T21:00:01Z").unwrap();
    assert_eq!(repeated.filled, "0.4");
    assert_eq!(
        book.apply_fill("i-1", "f-x", "0.7", "2026-10-22T21:00:02Z"),
        Err(OmsError::Quantity)
    );
    assert_eq!(book.order("i-1").unwrap().filled, "0.4");
    let filled = book.apply_fill("i-1", "f-2", "0.6", "2026-10-22T21:00:03Z").unwrap();
    assert_eq!(filled.state, OrderState::Filled);
    assert_eq!(filled.remainder, "0");
    assert_eq!(book.events().last().unwrap().kind, "fill");
    assert_eq!(
        book.apply_fill("i-1", "f-3", "0.1", "2026-10-22T21:00:03Z"),
        Err(OmsError::State)
    );
    assert_eq!(broker.submits.len(), 1);
}

#[test]
fn cancellation_is_idempotent() {
    let mut book = Book::default();
    let mut broker = Fake::new();
    broker.submit_script.push(ack(None));
    broker.cancel_script.push(ack(None));
    let approved = verdict("i-1", Decision::Allow, "", true);
    book.submit(&approved, &request("i-1"), &mut broker).unwrap();
    let cancelled = book.cancel("i-1", &mut broker).unwrap();
    assert_eq!(cancelled.state, OrderState::Cancelled);
    let again = book.cancel("i-1", &mut broker).unwrap();
    assert_eq!(again, cancelled);
    assert_eq!(broker.cancels, 1);
}

#[test]
fn a_cancel_timeout_is_not_sent_again_without_a_query() {
    let mut book = Book::default();
    let mut broker = Fake::new();
    broker.submit_script.push(ack(None));
    let approved = verdict("i-1", Decision::Allow, "", true);
    book.submit(&approved, &request("i-1"), &mut broker).unwrap();
    let waiting = book.cancel("i-1", &mut broker).unwrap();
    assert!(waiting.uncertain);
    assert_eq!(waiting.state, OrderState::Submitted);
    assert_eq!(book.cancel("i-1", &mut broker), Err(OmsError::AwaitingBroker));
    assert_eq!(broker.cancels, 1);
    assert_eq!(book.manual_reconciliation()[0].reason, "cancel_timeout");
}

#[test]
fn sized_approval_uses_the_verdict_size() {
    let mut book = Book::default();
    let mut broker = Fake::new();
    broker.submit_script.push(ack(None));
    let sized = verdict("i-1", Decision::AllowWithSize, "0.5", true);
    let order = book.submit(&sized, &request("i-1"), &mut broker).unwrap();
    assert_eq!(order.quantity, "0.5");
    let mut larger = Book::default();
    let mut quiet = Fake::new();
    let grown = verdict("i-2", Decision::AllowWithSize, "2", true);
    assert_eq!(larger.submit(&grown, &request("i-2"), &mut quiet), Err(OmsError::Quantity));
    assert!(quiet.submits.is_empty());
}

#[test]
fn the_book_stays_on_group_a() {
    let mut book = Book::default();
    let mut broker = Fake::new();
    broker.submit_script.push(ack(None));
    let approved = verdict("i-1", Decision::Allow, "", true);
    let mut other = request("i-1");
    other.group = "B".to_string();
    assert_eq!(book.submit(&approved, &other, &mut broker), Err(OmsError::Scope));
    let mut spaced = request("i 1");
    spaced.intent_id = "i 1".to_string();
    let spaced_verdict = verdict("i 1", Decision::Allow, "", true);
    assert_eq!(book.submit(&spaced_verdict, &spaced, &mut broker), Err(OmsError::Record));
    assert!(broker.submits.is_empty());
}

#[test]
fn a_broker_query_adopts_the_reported_fill_without_another_submit() {
    let mut book = Book::default();
    let mut broker = Fake::new();
    let approved = verdict("i-1", Decision::Allow, "", true);
    book.submit(&approved, &request("i-1"), &mut broker).unwrap();
    book.note_recon(true);
    broker.query_script.push(Ok(BrokerView::Working {
        broker_id: Some("T-7".to_string()),
        filled: "0.25".to_string(),
        fill_id: "f-9".to_string(),
        server_time: "2026-10-22T21:00:04Z".to_string(),
    }));
    let adopted = book.retry("i-1", &mut broker).unwrap();
    assert_eq!(adopted.state, OrderState::Partial);
    assert_eq!(adopted.filled, "0.25");
    assert_eq!(adopted.remainder, "0.75");
    assert_eq!(adopted.broker_id.as_deref(), Some("T-7"));
    assert_eq!(broker.submits.len(), 1);
    assert_eq!(book.events().last().unwrap().kind, "partial");
}

#[test]
fn a_rejected_submit_is_not_sent_again() {
    let mut book = Book::default();
    let mut broker = Fake::new();
    broker.submit_script.push(Err(PortError::Rejected));
    let approved = verdict("i-1", Decision::Allow, "", true);
    let failed = book.submit(&approved, &request("i-1"), &mut broker).unwrap();
    assert_eq!(failed.state, OrderState::Failed);
    let again = book.submit(&approved, &request("i-1"), &mut broker).unwrap();
    assert_eq!(again.state, OrderState::Failed);
    assert_eq!(broker.submits.len(), 1);
    assert_eq!(book.dead_letter()[0].reason, "rejected");
    assert!(book.manual_reconciliation().is_empty());
}

#[test]
fn an_ambiguous_query_does_not_send_another_order() {
    let mut book = Book::default();
    let mut broker = Fake::new();
    let approved = verdict("i-1", Decision::Allow, "", true);
    book.submit(&approved, &request("i-1"), &mut broker).unwrap();
    assert_eq!(book.retry("i-1", &mut broker), Err(OmsError::Recon));
    assert_eq!(broker.queries, 0);
    book.note_recon(true);
    broker.query_script.push(Ok(BrokerView::Ambiguous));
    broker.query_script.push(Ok(BrokerView::Ambiguous));
    assert_eq!(book.retry("i-1", &mut broker), Err(OmsError::AwaitingBroker));
    assert_eq!(book.retry("i-1", &mut broker), Err(OmsError::AwaitingBroker));
    assert_eq!(broker.submits, vec!["A:i-1".to_string()]);
    assert!(book.manual_reconciliation().iter().any(|item| item.reason == "ambiguous"));
}

#[test]
fn a_filled_broker_order_is_not_cancelled() {
    let mut book = Book::default();
    let mut broker = Fake::new();
    let approved = verdict("i-1", Decision::Allow, "", true);
    book.submit(&approved, &request("i-1"), &mut broker).unwrap();
    broker.query_script.push(Ok(BrokerView::Working {
        broker_id: Some("T-3".to_string()),
        filled: "1".to_string(),
        fill_id: "f-full".to_string(),
        server_time: "2026-10-22T21:00:05Z".to_string(),
    }));
    let filled = book.cancel("i-1", &mut broker).unwrap();
    assert_eq!(filled.state, OrderState::Filled);
    assert_eq!(filled.remainder, "0");
    assert_eq!(broker.cancels, 0);
    assert_eq!(broker.submits.len(), 1);
}

#[test]
fn a_restored_order_is_not_submitted_again() {
    let mut book = Book::default();
    let mut broker = Fake::new();
    broker.submit_script.push(ack(Some("T-1")));
    let stored = Order {
        intent_id: "i-1".to_string(),
        client_id: "i-1".to_string(),
        correlation_id: "A:i-1".to_string(),
        instrument: "EURUSD".to_string(),
        side: "BUY".to_string(),
        quantity: "1".to_string(),
        filled: "0".to_string(),
        remainder: "1".to_string(),
        protective_stop: "1.08".to_string(),
        stop_quantity: "1".to_string(),
        reduce_only: false,
        state: OrderState::Submitted,
        broker_id: None,
        uncertain: false,
    };
    book.restore(&stored).unwrap();
    let approved = verdict("i-1", Decision::Allow, "", true);
    let order = book.submit(&approved, &request("i-1"), &mut broker).unwrap();
    assert_eq!(order.state, OrderState::Submitted);
    assert_eq!(order.correlation_id, "A:i-1");
    assert!(broker.submits.is_empty());
}

#[test]
fn ts13_risk_increasing_submit_requires_a_protective_stop() {
    let mut book = Book::default();
    let mut broker = Fake::new();
    let approved = verdict("i-1", Decision::Allow, "", true);
    let mut missing = request("i-1");
    missing.protective_stop.clear();
    assert_eq!(book.submit(&approved, &missing, &mut broker), Err(OmsError::Record));
    assert!(broker.submits.is_empty());
}

#[test]
fn ts12_partial_fill_keeps_the_protective_stop_on_the_order() {
    let mut book = Book::default();
    let mut broker = Fake::new();
    broker.submit_script.push(ack(Some("T-1")));
    let approved = verdict("i-1", Decision::Allow, "", true);
    book.submit(&approved, &request("i-1"), &mut broker).unwrap();
    let partial = book.apply_fill("i-1", "f-1", "0.4", "2026-10-22T21:00:01Z").unwrap();
    assert_eq!(partial.state, OrderState::Partial);
    assert_eq!(partial.protective_stop, "1.08");
    assert_eq!(partial.stop_quantity, "0.4");
    assert_eq!(partial.filled, "0.4");
}
