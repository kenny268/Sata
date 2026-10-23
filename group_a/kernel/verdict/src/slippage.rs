//! Rolling slippage budget (**A-EXE-04**) and fill measurement (**PERF**).
//! Up to 20 samples; any breach triggers L1 sizing.
//! Budgets are the design starting values. A live fill series is not claimed.

use crate::decimal::{self, cmp};

pub const WINDOW: usize = 20;

/// Starting budgets from the Group A design. Unknown instruments fail closed.
pub fn budget(instrument: &str) -> Option<&'static str> {
    match instrument {
        "EURUSD" => Some("0.00005"),
        "GBPJPY" => Some("0.02"),
        "XAUUSD" => Some("0.2"),
        "BTCUSD" => Some("50"),
        _ => None,
    }
}

/// Absolute price difference against the instrument budget. Missing prices fail closed.
pub fn within_budget(instrument: &str, expected: &str, fill: &str) -> bool {
    let Some(limit) = budget(instrument) else {
        return false;
    };
    let Some(delta) = abs_diff(expected, fill) else {
        return false;
    };
    matches!(cmp(&delta, limit), Some(std::cmp::Ordering::Less | std::cmp::Ordering::Equal))
}

fn abs_diff(left: &str, right: &str) -> Option<String> {
    let left_value = decimal::parse(left)?;
    let right_value = decimal::parse(right)?;
    let delta = if left_value >= right_value { left_value - right_value } else { right_value - left_value };
    Some(decimal::format(delta))
}

#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct SlippageWindow {
    within_budget: Vec<bool>,
}

impl SlippageWindow {
    pub fn record(&mut self, within_budget: bool) {
        if self.within_budget.len() >= WINDOW {
            self.within_budget.remove(0);
        }
        self.within_budget.push(within_budget);
    }

    pub fn breached(&self) -> bool {
        !self.within_budget.is_empty() && self.within_budget.iter().any(|ok| !*ok)
    }

    pub fn len(&self) -> usize {
        self.within_budget.len()
    }

    pub fn is_empty(&self) -> bool {
        self.within_budget.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::SlippageWindow;

    #[test]
    fn a_single_breach_in_the_window_triggers_l1() {
        let mut window = SlippageWindow::default();
        for _ in 0..19 {
            window.record(true);
        }
        assert!(!window.breached());
        window.record(false);
        assert!(window.breached());
    }

    #[test]
    fn the_window_keeps_at_most_twenty_samples() {
        let mut window = SlippageWindow::default();
        for _ in 0..25 {
            window.record(true);
        }
        assert_eq!(window.len(), 20);
    }

    #[test]
    fn eurusd_half_pip_is_inside_and_two_pips_breach() {
        assert!(super::within_budget("EURUSD", "1.0850", "1.08504"));
        assert!(!super::within_budget("EURUSD", "1.0850", "1.0852"));
        assert!(!super::within_budget("UNKNOWN", "1", "1"));
    }
}
