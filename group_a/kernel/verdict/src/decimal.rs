//! Non-negative decimal strings. Comparisons never use binary floats.

const SCALE: i128 = 100_000_000;

pub fn parse(text: &str) -> Option<i128> {
    if text.is_empty() || text.starts_with('+') || text.starts_with('-') {
        return None;
    }
    let (whole, frac) = match text.split_once('.') {
        Some((whole, frac)) => (whole, frac),
        None => (text, ""),
    };
    if whole.is_empty() || frac.len() > 8 {
        return None;
    }
    if !whole.chars().all(|item| item.is_ascii_digit()) || !frac.chars().all(|item| item.is_ascii_digit()) {
        return None;
    }
    if whole.len() > 1 && whole.starts_with('0') {
        return None;
    }
    let whole_value: i128 = whole.parse().ok()?;
    let mut frac_value: i128 = if frac.is_empty() { 0 } else { frac.parse().ok()? };
    for _ in frac.len()..8 {
        frac_value = frac_value.checked_mul(10)?;
    }
    whole_value.checked_mul(SCALE)?.checked_add(frac_value)
}

pub fn format(value: i128) -> String {
    let whole = value / SCALE;
    let frac = (value % SCALE).abs();
    if frac == 0 {
        return whole.to_string();
    }
    let mut digits = format!("{frac:08}");
    while digits.ends_with('0') {
        digits.pop();
    }
    format!("{whole}.{digits}")
}

pub fn cmp(left: &str, right: &str) -> Option<std::cmp::Ordering> {
    Some(parse(left)?.cmp(&parse(right)?))
}

/// `left * right / divisor`, rounded toward zero.
pub fn mul_div(left: &str, right: &str, divisor: &str) -> Option<String> {
    let divisor_value = parse(divisor)?;
    if divisor_value == 0 {
        return None;
    }
    let product = parse(left)?.checked_mul(parse(right)?)?;
    Some(format(product / divisor_value))
}

pub fn percent_of(amount: &str, percent: &str) -> Option<String> {
    mul_div(amount, percent, "100")
}

pub fn add(left: &str, right: &str) -> Option<String> {
    let sum = parse(left)?.checked_add(parse(right)?)?;
    Some(format(sum))
}

pub fn sub(left: &str, right: &str) -> Option<String> {
    let difference = parse(left)?.checked_sub(parse(right)?)?;
    if difference < 0 {
        return None;
    }
    Some(format(difference))
}
