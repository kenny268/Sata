//! KERNEL-A process stub. It refuses to start without a signed release and constitution.

mod release;

fn main() {
    let path = match std::env::var("SATE_CONSTITUTION") {
        Ok(value) if !value.is_empty() => value,
        _ => refuse("constitution path is required"),
    };
    let public_key = match std::env::var("SATE_CONSTITUTION_PUBLIC_KEY") {
        Ok(value) if !value.is_empty() => value,
        _ => refuse("constitution verify key is required"),
    };
    let key_id = match std::env::var("SATE_CONSTITUTION_KEY_ID") {
        Ok(value) if !value.is_empty() => value,
        _ => refuse("constitution key id is required"),
    };
    let text = match std::fs::read_to_string(&path) {
        Ok(value) => value,
        Err(_) => refuse("constitution file is missing"),
    };
    let expected = match std::env::var("SATE_CONSTITUTION_VERSION") {
        Ok(value) => match value.parse::<u64>() {
            Ok(version) if version >= 1 => version,
            _ => refuse("constitution version pin is required"),
        },
        Err(_) => refuse("constitution version pin is required"),
    };
    let release_path = match std::env::var("SATE_RELEASE") {
        Ok(value) if !value.is_empty() => value,
        _ => refuse("signed kernel artifact is required"),
    };
    let build_key = match std::env::var("SATE_BUILD_PUBLIC_KEY") {
        Ok(value) if !value.is_empty() => value,
        _ => refuse("build verify key is required"),
    };
    let build_key_id = match std::env::var("SATE_BUILD_KEY_ID") {
        Ok(value) if !value.is_empty() => value,
        _ => refuse("build key id is required"),
    };
    let release_text = match std::fs::read_to_string(&release_path) {
        Ok(value) => value,
        Err(_) => refuse("signed kernel artifact is missing"),
    };
    let binary_path = match std::env::var("SATE_RELEASE_BINARY") {
        Ok(value) if !value.is_empty() => value,
        _ => match std::env::current_exe() {
            Ok(value) => value.to_string_lossy().into_owned(),
            Err(_) => refuse("kernel binary is missing"),
        },
    };
    let binary = match std::fs::read(&binary_path) {
        Ok(value) => value,
        Err(_) => refuse("kernel binary is missing"),
    };
    let constitution_hash = pinned_constitution_hash(&text);
    if let Err(error) = release::accept(
        &release_text,
        &binary,
        &build_key,
        &build_key_id,
        &key_id,
        expected,
        &constitution_hash,
    ) {
        refuse(&error.to_string());
    }
    let authorization_path = match std::env::var("SATE_RELEASE_AUTHORIZATION") {
        Ok(value) if !value.is_empty() => value,
        _ => refuse("deploy authorization is required"),
    };
    let deploy_key = match std::env::var("SATE_DEPLOY_PUBLIC_KEY") {
        Ok(value) if !value.is_empty() => value,
        _ => refuse("deploy verify key is required"),
    };
    let deploy_key_id = match std::env::var("SATE_DEPLOY_KEY_ID") {
        Ok(value) if !value.is_empty() => value,
        _ => refuse("deploy key id is required"),
    };
    let authorization_text = match std::fs::read_to_string(&authorization_path) {
        Ok(value) => value,
        Err(_) => refuse("deploy authorization is missing"),
    };
    if let Err(error) = release::authorize(
        &authorization_text,
        &release_text,
        &deploy_key,
        &deploy_key_id,
        &build_key_id,
        &key_id,
    ) {
        refuse(&error.to_string());
    }
    let rcb_version = match std::env::var("SATE_RCB_VERSION") {
        Ok(value) => match value.parse::<u64>() {
            Ok(version) if version >= 1 => version,
            _ => refuse("rcb version is required"),
        },
        Err(_) => refuse("rcb version is required"),
    };
    let mode = match std::env::var("SATE_MODE") {
        Ok(value) if !value.is_empty() => value,
        _ => refuse("constitution mode is required"),
    };
    let halt_path = match std::env::var("SATE_HALT_FILE") {
        Ok(value) if !value.is_empty() => value,
        _ => refuse("halt file path is required"),
    };
    let halt = match sate_a_verdict::read_halt(std::path::Path::new(&halt_path)) {
        Ok(record) => record,
        Err(sate_a_verdict::HaltError::Missing) => sate_a_verdict::HaltRecord::clear(),
        Err(sate_a_verdict::HaltError::Malformed) => refuse("halt file is malformed"),
    };
    let credential_key = match std::env::var("SATE_CREDENTIAL_KEY") {
        Ok(value) if !value.is_empty() => value,
        _ => refuse("credential key path is required"),
    };
    let credential_vault = match std::env::var("SATE_CREDENTIAL_VAULT") {
        Ok(value) if !value.is_empty() => value,
        _ => refuse("credential vault path is required"),
    };
    let audit = match sate_a_credentials::inject_at_startup(
        std::path::Path::new(&credential_key),
        std::path::Path::new(&credential_vault),
        &mode,
        &halt.kill_state,
    ) {
        Ok(audit) => audit,
        Err(error) => refuse(&error.to_string()),
    };
    let now = std::env::var("SATE_CONSTITUTION_NOW").unwrap_or_else(|_| utc_now());
    match sate_a_constitution::accept(&text, &public_key, &key_id, &now, Some(expected)) {
        Ok(version) => {
            let poll_secs = sate_a_verdict::POLL_INTERVAL_SECS;
            let halt_level = if halt.halt_level.is_empty() { "clear" } else { halt.halt_level.as_str() };
            println!(
                "kernel-a release ok constitution version {version} rcb version {rcb_version} mode {mode} halt {halt_level} credential {id} key {key} poll_secs {poll_secs}",
                id = audit.credential_id,
                key = audit.key_id,
            );
        }
        Err(error) => refuse(&error.to_string()),
    }
}

fn pinned_constitution_hash(text: &str) -> String {
    let value: serde_json::Value = match serde_json::from_str(text) {
        Ok(value) => value,
        Err(_) => refuse("constitution artifact is malformed"),
    };
    let canonical = match value.get("canonical").and_then(|item| item.as_str()) {
        Some(value) => value,
        None => refuse("constitution artifact is malformed"),
    };
    let claimed = match value.get("payload_hash").and_then(|item| item.as_str()) {
        Some(value) => value,
        None => refuse("constitution artifact is malformed"),
    };
    let digest = release::sha256_hex(canonical.as_bytes());
    if digest != claimed {
        refuse("constitution hash does not match the pin");
    }
    digest
}

fn refuse(reason: &str) -> ! {
    eprintln!("kernel-a refused: {reason}");
    std::process::exit(1);
}

fn utc_now() -> String {
    let seconds = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|duration| duration.as_secs())
        .unwrap_or(0);
    format_unix(seconds)
}

fn format_unix(seconds: u64) -> String {
    let days = seconds / 86_400;
    let time = seconds % 86_400;
    let (year, month, day) = civil_from_days(days as i64);
    let hour = time / 3_600;
    let minute = (time % 3_600) / 60;
    let second = time % 60;
    format!("{year:04}-{month:02}-{day:02}T{hour:02}:{minute:02}:{second:02}Z")
}

fn civil_from_days(days: i64) -> (i64, u32, u32) {
    let z = days + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = (z - era * 146_097) as u64;
    let yoe = (doe - doe / 1_460 + doe / 36_524 - doe / 146_096) / 365;
    let year = yoe as i64 + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let day = (doy - (153 * mp + 2) / 5 + 1) as u32;
    let month = (if mp < 10 { mp + 3 } else { mp - 9 }) as u32;
    let year = if month <= 2 { year + 1 } else { year };
    (year, month, day)
}
