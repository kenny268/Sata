//! Owner check-in dead-man timer (**A-CHK-03**, **OP-05**).

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CheckinError {
    AwayDays,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CheckinChannel {
    WebPasskey,
    TelegramAlive,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CheckinTier {
    Ok,
    Reminder,
    ManageOnly,
    Flatten,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CheckinBook {
    pub last_day: u64,
    pub current_day: u64,
    pub away_until_day: u64,
    pub reminder_days: u32,
    pub manage_only_days: u32,
    pub flatten_days: u32,
    pub max_away_days: u32,
}

impl Default for CheckinBook {
    fn default() -> Self {
        Self {
            last_day: 0,
            current_day: 0,
            away_until_day: 0,
            reminder_days: 7,
            manage_only_days: 10,
            flatten_days: 14,
            max_away_days: 30,
        }
    }
}

pub fn days_without(book: &CheckinBook) -> u64 {
    if book.away_until_day > 0 && book.current_day <= book.away_until_day {
        return 0;
    }
    book.current_day.saturating_sub(book.last_day)
}

pub fn tier(book: &CheckinBook) -> CheckinTier {
    let days = days_without(book);
    if days >= book.flatten_days as u64 {
        CheckinTier::Flatten
    } else if days >= book.manage_only_days as u64 {
        CheckinTier::ManageOnly
    } else if days >= book.reminder_days as u64 {
        CheckinTier::Reminder
    } else {
        CheckinTier::Ok
    }
}

pub fn record(book: &mut CheckinBook, channel: CheckinChannel) {
    let _ = channel;
    book.last_day = book.current_day;
}

pub fn set_away(book: &mut CheckinBook, days: u32) -> Result<(), CheckinError> {
    if days == 0 || days > book.max_away_days {
        return Err(CheckinError::AwayDays);
    }
    book.away_until_day = book.current_day.saturating_add(u64::from(days));
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{CheckinBook, CheckinTier, days_without, record, set_away, tier, CheckinChannel};

    #[test]
    fn away_pauses_the_lapse_counter() {
        let mut book = CheckinBook {
            last_day: 0,
            current_day: 12,
            away_until_day: 15,
            ..CheckinBook::default()
        };
        assert_eq!(days_without(&book), 0);
        assert_eq!(tier(&book), CheckinTier::Ok);
        book.current_day = 16;
        assert_eq!(days_without(&book), 16);
        assert_eq!(tier(&book), CheckinTier::Flatten);
    }

    #[test]
    fn day10_and_day14_tiers_match_constitution_defaults() {
        let book = CheckinBook {
            last_day: 0,
            current_day: 10,
            ..CheckinBook::default()
        };
        assert_eq!(tier(&book), CheckinTier::ManageOnly);
        let book = CheckinBook {
            last_day: 0,
            current_day: 14,
            ..CheckinBook::default()
        };
        assert_eq!(tier(&book), CheckinTier::Flatten);
    }

    #[test]
    fn record_and_away_follow_owner_rules() {
        let mut book = CheckinBook {
            current_day: 5,
            ..CheckinBook::default()
        };
        record(&mut book, CheckinChannel::WebPasskey);
        assert_eq!(book.last_day, 5);
        set_away(&mut book, 7).unwrap();
        assert_eq!(book.away_until_day, 12);
    }
}
