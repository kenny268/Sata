//! One lifecycle per intent. A timeout is queried before another broker submit.
//! Dead-letter and manual reconciliation lists are records for a later page.

use std::cmp::Ordering;
use std::fmt;

use sate_a_verdict::{add, cmp, sub, Decision, Verdict};

pub fn accept_verdict(decision: Decision) -> Result<(), &'static str> {
    if decision.allows_broker_submit() {
        Ok(())
    } else {
        Err("no broker order without an allow verdict")
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OmsError {
    Verdict,
    Scope,
    Record,
    State,
    Quantity,
    AwaitingBroker,
    Recon,
}

impl fmt::Display for OmsError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self {
            Self::Verdict => "no broker order without an allow verdict",
            Self::Scope => "the order manager stays on group A",
            Self::Record => "the order record is incomplete",
            Self::State => "the order stays in its current state",
            Self::Quantity => "the fill does not fit the order",
            Self::AwaitingBroker => "a timeout is queried before another submit",
            Self::Recon => "a retry waits until reconciliation is clean",
        })
    }
}

impl std::error::Error for OmsError {}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OrderState {
    New,
    Submitted,
    Partial,
    Filled,
    Cancelled,
    Failed,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PortError {
    Timeout,
    Rejected,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Ack {
    pub broker_id: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BrokerView {
    Absent,
    Ambiguous,
    Working {
        broker_id: Option<String>,
        filled: String,
        fill_id: String,
        server_time: String,
    },
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SubmitRequest {
    pub client_id: String,
    pub correlation_id: String,
    pub instrument: String,
    pub side: String,
    pub quantity: String,
    pub protective_stop: String,
    pub reduce_only: bool,
}

pub trait BrokerPort {
    fn submit(&mut self, request: &SubmitRequest) -> Result<Ack, PortError>;
    fn cancel(&mut self, correlation_id: &str) -> Result<Ack, PortError>;
    fn query(&mut self, correlation_id: &str) -> Result<BrokerView, PortError>;
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Submission {
    pub intent_id: String,
    pub group: String,
    pub instrument: String,
    pub side: String,
    pub quantity: String,
    pub protective_stop: String,
    pub reduce_only: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Order {
    pub intent_id: String,
    pub client_id: String,
    pub correlation_id: String,
    pub instrument: String,
    pub side: String,
    pub quantity: String,
    pub filled: String,
    pub remainder: String,
    pub protective_stop: String,
    pub stop_quantity: String,
    pub reduce_only: bool,
    pub state: OrderState,
    pub broker_id: Option<String>,
    pub uncertain: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LifecycleEvent {
    pub intent_id: String,
    pub correlation_id: String,
    pub fill_id: String,
    pub kind: &'static str,
    pub quantity: String,
    pub filled: String,
    pub remainder: String,
    pub server_time: String,
    pub state: OrderState,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct QueueHook {
    pub intent_id: String,
    pub correlation_id: String,
    pub state: OrderState,
    pub reason: &'static str,
}

#[derive(Debug, Default)]
pub struct Book {
    orders: Vec<Order>,
    events: Vec<LifecycleEvent>,
    dead_letter: Vec<QueueHook>,
    manual: Vec<QueueHook>,
    recon_clear: bool,
}

impl Book {
    pub fn submit(
        &mut self,
        verdict: &Verdict,
        request: &Submission,
        broker: &mut impl BrokerPort,
    ) -> Result<Order, OmsError> {
        if let Some(existing) = self.order(&request.intent_id) {
            return Ok(existing.clone());
        }
        let quantity = approved_quantity(verdict, request)?;
        let (client_id, correlation_id) = correlation(&request.intent_id);
        let order = Order {
            intent_id: request.intent_id.clone(),
            client_id,
            correlation_id,
            instrument: request.instrument.clone(),
            side: request.side.clone(),
            quantity: quantity.clone(),
            filled: "0".to_string(),
            remainder: quantity.clone(),
            protective_stop: request.protective_stop.clone(),
            stop_quantity: quantity.clone(),
            reduce_only: request.reduce_only,
            state: OrderState::New,
            broker_id: None,
            uncertain: false,
        };
        let submit = SubmitRequest {
            client_id: order.client_id.clone(),
            correlation_id: order.correlation_id.clone(),
            instrument: order.instrument.clone(),
            side: order.side.clone(),
            quantity,
            protective_stop: order.protective_stop.clone(),
            reduce_only: order.reduce_only,
        };
        self.orders.push(order);
        let result = broker.submit(&submit);
        self.finish_submit(&request.intent_id, result)
    }

    pub fn retry(
        &mut self,
        intent_id: &str,
        broker: &mut impl BrokerPort,
    ) -> Result<Order, OmsError> {
        if !self.recon_clear {
            return Err(OmsError::Recon);
        }
        let order = self.order(intent_id).ok_or(OmsError::Record)?.clone();
        if !order.uncertain {
            return Ok(order);
        }
        if order.state != OrderState::New {
            return Err(OmsError::State);
        }
        let view = match broker.query(&order.correlation_id) {
            Ok(view) => view,
            Err(_) => return Err(OmsError::AwaitingBroker),
        };
        match view {
            BrokerView::Absent => self.send_existing(&order, broker),
            BrokerView::Ambiguous => {
                self.hold(intent_id, "ambiguous");
                Err(OmsError::AwaitingBroker)
            }
            working => self.adopt(intent_id, working),
        }
    }

    pub fn cancel(
        &mut self,
        intent_id: &str,
        broker: &mut impl BrokerPort,
    ) -> Result<Order, OmsError> {
        let order = self.order(intent_id).ok_or(OmsError::Record)?.clone();
        if order.state == OrderState::Cancelled {
            return Ok(order);
        }
        if matches!(order.state, OrderState::Filled | OrderState::Failed) {
            return Err(OmsError::State);
        }
        if order.uncertain {
            return self.cancel_uncertain(order, broker);
        }
        let result = broker.cancel(&order.correlation_id);
        match result {
            Ok(ack) => self.mark_cancelled(intent_id, clean_broker_id(ack.broker_id)),
            Err(PortError::Timeout) => {
                self.hold(intent_id, "cancel_timeout");
                self.order(intent_id).cloned().ok_or(OmsError::Record)
            }
            Err(PortError::Rejected) => {
                self.hold(intent_id, "cancel_rejected");
                Err(OmsError::State)
            }
        }
    }

    pub fn apply_fill(
        &mut self,
        intent_id: &str,
        fill_id: &str,
        quantity: &str,
        server_time: &str,
    ) -> Result<Order, OmsError> {
        if fill_id.is_empty() || blank(server_time) {
            return Err(OmsError::Record);
        }
        if let Some(event) = self.events.iter().find(|event| event.fill_id == fill_id) {
            if event.intent_id == intent_id {
                return self.order(intent_id).cloned().ok_or(OmsError::Record);
            }
            return Err(OmsError::Record);
        }
        let order = self.order(intent_id).ok_or(OmsError::Record)?.clone();
        if !matches!(order.state, OrderState::Submitted | OrderState::Partial) || order.uncertain {
            return Err(OmsError::State);
        }
        if cmp(quantity, "0").ok_or(OmsError::Quantity)? != Ordering::Greater {
            return Err(OmsError::Quantity);
        }
        let filled = add(&order.filled, quantity).ok_or(OmsError::Quantity)?;
        let compared = cmp(&filled, &order.quantity).ok_or(OmsError::Quantity)?;
        if compared == Ordering::Greater {
            return Err(OmsError::Quantity);
        }
        let remainder = sub(&order.quantity, &filled).ok_or(OmsError::Quantity)?;
        let state = if compared == Ordering::Equal {
            OrderState::Filled
        } else {
            OrderState::Partial
        };
        let kind = if state == OrderState::Filled { "fill" } else { "partial" };
        self.write(intent_id, state, &filled, &remainder, None, false);
        if let Some(index) = self.index(intent_id) {
            self.orders[index].stop_quantity = filled.clone();
        }
        self.record(intent_id, fill_id, kind, quantity, server_time);
        self.order(intent_id).cloned().ok_or(OmsError::Record)
    }

    pub fn restore(&mut self, snapshot: &Order) -> Result<Order, OmsError> {
        if let Some(existing) = self.order(&snapshot.intent_id) {
            return Ok(existing.clone());
        }
        let (client_id, correlation_id) = correlation(&snapshot.intent_id);
        if snapshot.client_id != client_id || snapshot.correlation_id != correlation_id {
            return Err(OmsError::Record);
        }
        if blank(&snapshot.intent_id)
            || blank(&snapshot.instrument)
            || !matches!(snapshot.side.as_str(), "BUY" | "SELL")
        {
            return Err(OmsError::Record);
        }
        if snapshot.broker_id.as_ref().is_some_and(|value| blank(value)) {
            return Err(OmsError::Record);
        }
        if cmp(&snapshot.quantity, "0").ok_or(OmsError::Quantity)? != Ordering::Greater {
            return Err(OmsError::Quantity);
        }
        let remainder = sub(&snapshot.quantity, &snapshot.filled).ok_or(OmsError::Quantity)?;
        if snapshot.remainder != remainder {
            return Err(OmsError::Quantity);
        }
        let filled_vs_zero = cmp(&snapshot.filled, "0").ok_or(OmsError::Quantity)?;
        let filled_vs_quantity = cmp(&snapshot.filled, &snapshot.quantity).ok_or(OmsError::Quantity)?;
        let consistent = match snapshot.state {
            OrderState::New => filled_vs_zero == Ordering::Equal && snapshot.uncertain,
            OrderState::Submitted => filled_vs_zero == Ordering::Equal && !snapshot.uncertain,
            OrderState::Partial => {
                filled_vs_zero == Ordering::Greater && filled_vs_quantity == Ordering::Less
            }
            OrderState::Filled => filled_vs_quantity == Ordering::Equal,
            OrderState::Cancelled | OrderState::Failed => true,
        };
        if !consistent {
            return Err(OmsError::State);
        }
        self.orders.push(snapshot.clone());
        if snapshot.uncertain {
            self.enqueue(&snapshot.intent_id, "timeout", true);
        }
        Ok(snapshot.clone())
    }

    pub fn order(&self, intent_id: &str) -> Option<&Order> {
        self.orders.iter().find(|order| order.intent_id == intent_id)
    }

    pub fn events(&self) -> &[LifecycleEvent] {
        &self.events
    }

    pub fn dead_letter(&self) -> &[QueueHook] {
        &self.dead_letter
    }

    pub fn manual_reconciliation(&self) -> &[QueueHook] {
        &self.manual
    }

    pub fn note_recon(&mut self, allows_retry: bool) {
        self.recon_clear = allows_retry;
    }

    fn finish_submit(
        &mut self,
        intent_id: &str,
        result: Result<Ack, PortError>,
    ) -> Result<Order, OmsError> {
        match result {
            Ok(ack) => {
                let broker_id = clean_broker_id(ack.broker_id);
                self.write(intent_id, OrderState::Submitted, "0", "", broker_id, false);
                self.record(intent_id, "", "submit", "0", "");
                self.order(intent_id).cloned().ok_or(OmsError::Record)
            }
            Err(PortError::Timeout) => {
                self.hold(intent_id, "timeout");
                self.order(intent_id).cloned().ok_or(OmsError::Record)
            }
            Err(PortError::Rejected) => {
                self.write(intent_id, OrderState::Failed, "0", "0", None, false);
                self.enqueue(intent_id, "rejected", false);
                self.record(intent_id, "", "fail", "0", "");
                self.order(intent_id).cloned().ok_or(OmsError::Record)
            }
        }
    }

    fn send_existing(
        &mut self,
        previous: &Order,
        broker: &mut impl BrokerPort,
    ) -> Result<Order, OmsError> {
        let request = SubmitRequest {
            client_id: previous.client_id.clone(),
            correlation_id: previous.correlation_id.clone(),
            instrument: previous.instrument.clone(),
            side: previous.side.clone(),
            quantity: previous.quantity.clone(),
            protective_stop: previous.protective_stop.clone(),
            reduce_only: previous.reduce_only,
        };
        let intent_id = previous.intent_id.clone();
        let result = broker.submit(&request);
        self.clear_queues(&intent_id);
        self.finish_submit(&intent_id, result)
    }

    fn adopt(&mut self, intent_id: &str, view: BrokerView) -> Result<Order, OmsError> {
        let BrokerView::Working {
            broker_id,
            filled,
            fill_id,
            server_time,
        } = view
        else {
            return Err(OmsError::AwaitingBroker);
        };
        let quantity = self.order(intent_id).ok_or(OmsError::Record)?.quantity.clone();
        let compared = cmp(&filled, &quantity).ok_or(OmsError::Quantity)?;
        let no_fill = cmp(&filled, "0").ok_or(OmsError::Quantity)? == Ordering::Equal;
        if compared == Ordering::Greater || (!no_fill && (fill_id.is_empty() || blank(&server_time))) {
            self.hold(intent_id, "ambiguous");
            return Err(OmsError::AwaitingBroker);
        }
        let filled_text = if no_fill {
            "0".to_string()
        } else {
            add(&filled, "0").ok_or(OmsError::Quantity)?
        };
        let remainder = sub(&quantity, &filled_text).ok_or(OmsError::Quantity)?;
        let state = if no_fill {
            OrderState::Submitted
        } else if compared == Ordering::Equal {
            OrderState::Filled
        } else {
            OrderState::Partial
        };
        self.clear_queues(intent_id);
        self.write(
            intent_id,
            state,
            &filled_text,
            &remainder,
            clean_broker_id(broker_id),
            false,
        );
        if !no_fill {
            let kind = if state == OrderState::Filled { "fill" } else { "partial" };
            self.record(intent_id, &fill_id, kind, &filled_text, &server_time);
        }
        self.order(intent_id).cloned().ok_or(OmsError::Record)
    }

    fn cancel_uncertain(
        &mut self,
        order: Order,
        broker: &mut impl BrokerPort,
    ) -> Result<Order, OmsError> {
        let view = match broker.query(&order.correlation_id) {
            Ok(view) => view,
            Err(_) => return Err(OmsError::AwaitingBroker),
        };
        match view {
            BrokerView::Absent => self.mark_cancelled(&order.intent_id, None),
            BrokerView::Ambiguous => {
                self.hold(&order.intent_id, "ambiguous");
                Err(OmsError::AwaitingBroker)
            }
            working => {
                let intent_id = order.intent_id.clone();
                let correlation_id = order.correlation_id.clone();
                let adopted = self.adopt(&intent_id, working)?;
                if adopted.state == OrderState::Filled {
                    return Ok(adopted);
                }
                match broker.cancel(&correlation_id) {
                    Ok(_) => self.mark_cancelled(&intent_id, None),
                    Err(PortError::Timeout) => {
                        self.hold(&intent_id, "cancel_timeout");
                        self.order(&intent_id).cloned().ok_or(OmsError::Record)
                    }
                    Err(PortError::Rejected) => Err(OmsError::State),
                }
            }
        }
    }

    fn mark_cancelled(
        &mut self,
        intent_id: &str,
        broker_id: Option<String>,
    ) -> Result<Order, OmsError> {
        let order = self.order(intent_id).ok_or(OmsError::Record)?.clone();
        self.clear_queues(intent_id);
        self.write(
            intent_id,
            OrderState::Cancelled,
            &order.filled,
            &order.remainder,
            broker_id.or(order.broker_id),
            false,
        );
        self.record(intent_id, "", "cancel", "0", "");
        self.order(intent_id).cloned().ok_or(OmsError::Record)
    }

    fn hold(&mut self, intent_id: &str, reason: &'static str) {
        if let Some(index) = self.index(intent_id) {
            self.orders[index].uncertain = true;
        }
        let known = self
            .manual
            .iter()
            .any(|item| item.intent_id == intent_id && item.reason == reason);
        self.enqueue(intent_id, reason, true);
        if !known {
            self.record(intent_id, "", "timeout", "0", "");
        }
    }

    fn write(
        &mut self,
        intent_id: &str,
        state: OrderState,
        filled: &str,
        remainder: &str,
        broker_id: Option<String>,
        uncertain: bool,
    ) {
        let Some(index) = self.index(intent_id) else {
            return;
        };
        let order = &mut self.orders[index];
        order.state = state;
        if !filled.is_empty() {
            order.filled = filled.to_string();
        }
        if !remainder.is_empty() {
            order.remainder = remainder.to_string();
        }
        if broker_id.is_some() {
            order.broker_id = broker_id;
        }
        order.uncertain = uncertain;
    }

    fn record(
        &mut self,
        intent_id: &str,
        fill_id: &str,
        kind: &'static str,
        quantity: &str,
        server_time: &str,
    ) {
        let Some(index) = self.index(intent_id) else {
            return;
        };
        let intent = self.orders[index].intent_id.clone();
        let correlation_id = self.orders[index].correlation_id.clone();
        let filled = self.orders[index].filled.clone();
        let remainder = self.orders[index].remainder.clone();
        let state = self.orders[index].state;
        self.events.push(LifecycleEvent {
            intent_id: intent,
            correlation_id,
            fill_id: fill_id.to_string(),
            kind,
            quantity: quantity.to_string(),
            filled,
            remainder,
            server_time: server_time.to_string(),
            state,
        });
    }

    fn enqueue(&mut self, intent_id: &str, reason: &'static str, manual: bool) {
        let Some(index) = self.index(intent_id) else {
            return;
        };
        let hook = QueueHook {
            intent_id: self.orders[index].intent_id.clone(),
            correlation_id: self.orders[index].correlation_id.clone(),
            state: self.orders[index].state,
            reason,
        };
        let seen = self
            .dead_letter
            .iter()
            .any(|item| item.intent_id == hook.intent_id && item.reason == reason);
        if !seen {
            self.dead_letter.push(hook.clone());
        }
        let queued = self
            .manual
            .iter()
            .any(|item| item.intent_id == hook.intent_id && item.reason == reason);
        if manual && !queued {
            self.manual.push(hook);
        }
    }

    fn clear_queues(&mut self, intent_id: &str) {
        self.dead_letter.retain(|item| item.intent_id != intent_id);
        self.manual.retain(|item| item.intent_id != intent_id);
    }

    fn index(&self, intent_id: &str) -> Option<usize> {
        self.orders.iter().position(|order| order.intent_id == intent_id)
    }
}

fn approved_quantity(verdict: &Verdict, request: &Submission) -> Result<String, OmsError> {
    if !verdict.persisted || !verdict.decision.allows_broker_submit() {
        return Err(OmsError::Verdict);
    }
    if verdict.intent_id != request.intent_id || request.group != "A" {
        return Err(OmsError::Scope);
    }
    if blank(&request.intent_id) || blank(&request.instrument) || !matches!(request.side.as_str(), "BUY" | "SELL") {
        return Err(OmsError::Record);
    }
    if cmp(&request.quantity, "0").ok_or(OmsError::Quantity)? != Ordering::Greater {
        return Err(OmsError::Quantity);
    }
    if request.reduce_only {
        if !request.protective_stop.is_empty() && cmp(&request.protective_stop, "0").is_none() {
            return Err(OmsError::Record);
        }
    } else if cmp(&request.protective_stop, "0").ok_or(OmsError::Record)? != Ordering::Greater {
        return Err(OmsError::Record);
    }
    if verdict.decision == Decision::AllowWithSize {
        if cmp(&verdict.size, "0").ok_or(OmsError::Quantity)? != Ordering::Greater {
            return Err(OmsError::Quantity);
        }
        if cmp(&verdict.size, &request.quantity).ok_or(OmsError::Quantity)? == Ordering::Greater {
            return Err(OmsError::Quantity);
        }
        return Ok(verdict.size.clone());
    }
    Ok(request.quantity.clone())
}

fn correlation(intent_id: &str) -> (String, String) {
    (intent_id.to_string(), format!("A:{intent_id}"))
}

fn clean_broker_id(broker_id: Option<String>) -> Option<String> {
    broker_id.filter(|value| !blank(value))
}

fn blank(value: &str) -> bool {
    value.is_empty() || value.chars().any(char::is_whitespace)
}

#[cfg(test)]
mod tests;
