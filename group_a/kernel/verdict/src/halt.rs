//! Halt and kill state on disk. Restart reads the same file back.
//! The trading mode stays with the loaded constitution; the file does not replace it.

use std::fs;
use std::io::ErrorKind;
use std::path::Path;

use crate::engine::KernelBook;

#[derive(Debug, PartialEq, Eq)]
pub enum HaltError {
    Missing,
    Malformed,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HaltRecord {
    pub halt_level: String,
    pub kill_state: String,
    pub fingerprint: String,
    pub safe_mode: bool,
}

impl HaltRecord {
    pub fn clear() -> Self {
        Self {
            halt_level: String::new(),
            kill_state: String::new(),
            fingerprint: String::new(),
            safe_mode: false,
        }
    }
}

pub fn save(path: &Path, book: &KernelBook) -> Result<(), HaltError> {
    let safe = if book.safe_mode { "1" } else { "0" };
    let body = format!(
        "mode={}\nhalt={}\nkill={}\nfingerprint={}\nsafe_mode={safe}\n",
        book.mode, book.halt_level, book.kill_state, book.fingerprint
    );
    fs::write(path, body).map_err(|_| HaltError::Malformed)
}

pub fn read(path: &Path) -> Result<HaltRecord, HaltError> {
    let text = match fs::read_to_string(path) {
        Ok(value) => value,
        Err(error) if error.kind() == ErrorKind::NotFound => return Err(HaltError::Missing),
        Err(_) => return Err(HaltError::Malformed),
    };
    let mut mode_seen = false;
    let mut halt = None;
    let mut kill = None;
    let mut fingerprint = None;
    let mut safe = None;
    for line in text.lines() {
        if line.is_empty() {
            continue;
        }
        let Some((key, value)) = line.split_once('=') else {
            return Err(HaltError::Malformed);
        };
        match key {
            "mode" => mode_seen = true,
            "halt" => halt = Some(value.to_string()),
            "kill" => kill = Some(value.to_string()),
            "fingerprint" => fingerprint = Some(value.to_string()),
            "safe_mode" => {
                if value != "0" && value != "1" {
                    return Err(HaltError::Malformed);
                }
                safe = Some(value == "1");
            }
            _ => return Err(HaltError::Malformed),
        }
    }
    if !mode_seen {
        return Err(HaltError::Malformed);
    }
    Ok(HaltRecord {
        halt_level: halt.ok_or(HaltError::Malformed)?,
        kill_state: kill.ok_or(HaltError::Malformed)?,
        fingerprint: fingerprint.ok_or(HaltError::Malformed)?,
        safe_mode: safe.ok_or(HaltError::Malformed)?,
    })
}

pub fn apply(record: &HaltRecord, book: &mut KernelBook) {
    book.halt_level.clone_from(&record.halt_level);
    book.kill_state.clone_from(&record.kill_state);
    book.fingerprint.clone_from(&record.fingerprint);
    book.safe_mode = record.safe_mode;
}

pub fn load(path: &Path, book: &mut KernelBook) -> Result<(), HaltError> {
    apply(&read(path)?, book);
    Ok(())
}
