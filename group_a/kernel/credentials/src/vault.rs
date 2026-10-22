//! Sealed Exness credentials. The password never leaves this module.

use std::fmt;
use std::fs;
use std::path::Path;

use crate::aead;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VaultError {
    Key,
    Vault,
    Malformed,
    Crypto,
    Mode,
    LiveOnSim,
    Sealed,
    Secret,
}

impl fmt::Display for VaultError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        let text = match self {
            Self::Key => "credential key is missing",
            Self::Vault => "credential vault is missing",
            Self::Malformed => "credential vault is malformed",
            Self::Crypto => "credential vault failed authentication",
            Self::Mode => "credential mode does not match the kernel",
            Self::LiveOnSim => "live credentials are refused on a sim kernel",
            Self::Sealed => "credentials stay sealed after K3",
            Self::Secret => "credential audit cannot carry a secret",
        };
        formatter.write_str(text)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Audit {
    pub action: String,
    pub credential_id: String,
    pub key_id: String,
    pub previous_key_id: String,
    pub mode: String,
    pub purpose: String,
}

impl Audit {
    pub fn contains(&self, secret: &str) -> bool {
        if secret.is_empty() {
            return false;
        }
        [
            self.action.as_str(),
            self.credential_id.as_str(),
            self.key_id.as_str(),
            self.previous_key_id.as_str(),
            self.mode.as_str(),
            self.purpose.as_str(),
        ]
        .iter()
        .any(|field| field.contains(secret))
    }
}

struct Secret {
    login: Vec<u8>,
    password: Vec<u8>,
    server: Vec<u8>,
}

impl Drop for Secret {
    fn drop(&mut self) {
        wipe(&mut self.login);
        wipe(&mut self.password);
        wipe(&mut self.server);
    }
}

impl fmt::Debug for Secret {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("Secret(redacted)")
    }
}

struct Record {
    mode: String,
    credential_id: String,
    key_id: String,
    nonce: [u8; 12],
    body: Vec<u8>,
}

pub struct Material<'a> {
    pub mode: &'a str,
    pub credential_id: &'a str,
    pub key_id: &'a str,
    pub login: &'a str,
    pub password: &'a str,
    pub server: &'a str,
}

pub fn seal_text(key: &[u8; 32], material: &Material<'_>, nonce: &[u8; 12]) -> Result<String, VaultError> {
    check_label(
        material.mode,
        material.credential_id,
        material.key_id,
        material.login,
        material.password,
        material.server,
    )?;
    let secret = Secret {
        login: material.login.as_bytes().to_vec(),
        password: material.password.as_bytes().to_vec(),
        server: material.server.as_bytes().to_vec(),
    };
    let packed = pack(&secret)?;
    let sealed = aead::seal(key, nonce, &aad(material.mode, material.credential_id, material.key_id), &packed);
    wipe_vec(packed);
    Ok(render(&Record {
        mode: material.mode.to_string(),
        credential_id: material.credential_id.to_string(),
        key_id: material.key_id.to_string(),
        nonce: *nonce,
        body: sealed,
    }))
}

pub fn rotate_text(
    old_key: &[u8; 32],
    new_key: &[u8; 32],
    new_key_id: &str,
    text: &str,
    process_mode: &str,
    nonce: &[u8; 12],
) -> Result<(String, Audit), VaultError> {
    let record = parse(text)?;
    if old_key == new_key && nonce == &record.nonce {
        return Err(VaultError::Crypto);
    }
    let account = account_mode(process_mode, &record.mode)?;
    let secret = unseal(old_key, &record)?;
    check_label(&record.mode, &record.credential_id, new_key_id, secret.login_str(), secret.password_str(), secret.server_str())?;
    let packed = pack(&secret)?;
    let sealed = aead::seal(new_key, nonce, &aad(&record.mode, &record.credential_id, new_key_id), &packed);
    wipe_vec(packed);
    let audit = Audit {
        action: "rotate".to_string(),
        credential_id: record.credential_id.clone(),
        key_id: new_key_id.to_string(),
        previous_key_id: record.key_id,
        mode: account.to_string(),
        purpose: "rotation".to_string(),
    };
    if audit.contains(secret.password_str())
        || audit.contains(secret.login_str())
        || audit.contains(secret.server_str())
    {
        return Err(VaultError::Secret);
    }
    let text = render(&Record {
        mode: record.mode,
        credential_id: record.credential_id,
        key_id: new_key_id.to_string(),
        nonce: *nonce,
        body: sealed,
    });
    Ok((text, audit))
}

/// Load the vault once. The secret is wiped before this returns.
pub fn inject_at_startup(
    key_path: &Path,
    vault_path: &Path,
    process_mode: &str,
    kill_state: &str,
) -> Result<Audit, VaultError> {
    if kill_state == "K3" {
        return Err(VaultError::Sealed);
    }
    let key = load_key(key_path)?;
    let text = fs::read_to_string(vault_path).map_err(|_| VaultError::Vault)?;
    let record = parse(&text)?;
    let account = account_mode(process_mode, &record.mode)?;
    let secret = unseal(key.bytes(), &record)?;
    let audit = Audit {
        action: "inject".to_string(),
        credential_id: record.credential_id,
        key_id: record.key_id,
        previous_key_id: String::new(),
        mode: account.to_string(),
        purpose: "startup".to_string(),
    };
    if audit.contains(secret.password_str()) || audit.contains(secret.login_str()) || audit.contains(secret.server_str()) {
        return Err(VaultError::Secret);
    }
    Ok(audit)
}

fn account_mode<'a>(process_mode: &str, sealed_mode: &'a str) -> Result<&'a str, VaultError> {
    let expected = if process_mode == "SIM" {
        "SIM"
    } else if matches!(process_mode, "LIVE-L1" | "LIVE-L2" | "LIVE-L3") {
        "LIVE"
    } else {
        return Err(VaultError::Mode);
    };
    if expected == "SIM" && sealed_mode == "LIVE" {
        return Err(VaultError::LiveOnSim);
    }
    if sealed_mode != expected {
        return Err(VaultError::Mode);
    }
    Ok(sealed_mode)
}

fn unseal(key: &[u8; 32], record: &Record) -> Result<Secret, VaultError> {
    let plain = aead::open(key, &record.nonce, &aad(&record.mode, &record.credential_id, &record.key_id), &record.body)
        .ok_or(VaultError::Crypto)?;
    let secret = unpack(&plain)?;
    wipe_owned(plain);
    Ok(secret)
}

fn check_label(
    mode: &str,
    credential_id: &str,
    key_id: &str,
    login: &str,
    password: &str,
    server: &str,
) -> Result<(), VaultError> {
    if mode != "SIM" && mode != "LIVE" {
        return Err(VaultError::Mode);
    }
    if credential_id.is_empty() || key_id.is_empty() || login.is_empty() || password.is_empty() || server.is_empty() {
        return Err(VaultError::Malformed);
    }
    if credential_id.len() > 64 || key_id.len() > 64 || credential_id.contains('\n') || key_id.contains('\n') {
        return Err(VaultError::Malformed);
    }
    if credential_id.contains(password) || credential_id.contains(login) || key_id.contains(password) || key_id.contains(login) {
        return Err(VaultError::Secret);
    }
    Ok(())
}

fn pack(secret: &Secret) -> Result<Vec<u8>, VaultError> {
    let mut out = Vec::new();
    for field in [&secret.login, &secret.password, &secret.server] {
        if field.is_empty() || field.len() > 256 {
            return Err(VaultError::Malformed);
        }
        let len = u32::try_from(field.len()).map_err(|_| VaultError::Malformed)?;
        out.extend_from_slice(&len.to_le_bytes());
        out.extend_from_slice(field);
    }
    Ok(out)
}

fn unpack(bytes: &[u8]) -> Result<Secret, VaultError> {
    let mut offset = 0;
    let login = take(bytes, &mut offset)?;
    let password = take(bytes, &mut offset)?;
    let server = take(bytes, &mut offset)?;
    if offset != bytes.len() {
        return Err(VaultError::Malformed);
    }
    Ok(Secret { login, password, server })
}

fn take(bytes: &[u8], offset: &mut usize) -> Result<Vec<u8>, VaultError> {
    if *offset + 4 > bytes.len() {
        return Err(VaultError::Malformed);
    }
    let len = u32::from_le_bytes(bytes[*offset..*offset + 4].try_into().unwrap()) as usize;
    *offset += 4;
    if len == 0 || len > 256 || *offset + len > bytes.len() {
        return Err(VaultError::Malformed);
    }
    let field = bytes[*offset..*offset + len].to_vec();
    *offset += len;
    Ok(field)
}

fn aad(mode: &str, credential_id: &str, key_id: &str) -> Vec<u8> {
    format!("{mode}\n{credential_id}\n{key_id}").into_bytes()
}

fn render(record: &Record) -> String {
    format!(
        "sate-vault 1\nmode {}\ncredential_id {}\nkey_id {}\nnonce {}\nbody {}\n",
        record.mode,
        record.credential_id,
        record.key_id,
        encode_hex(&record.nonce),
        encode_hex(&record.body)
    )
}

fn parse(text: &str) -> Result<Record, VaultError> {
    let mut lines = text.lines();
    if lines.next() != Some("sate-vault 1") {
        return Err(VaultError::Malformed);
    }
    let mut mode = None;
    let mut credential_id = None;
    let mut key_id = None;
    let mut nonce = None;
    let mut body = None;
    for line in lines {
        if line.is_empty() {
            continue;
        }
        let Some((key, value)) = line.split_once(' ') else {
            return Err(VaultError::Malformed);
        };
        match key {
            "mode" => mode = Some(value.to_string()),
            "credential_id" => credential_id = Some(value.to_string()),
            "key_id" => key_id = Some(value.to_string()),
            "nonce" => nonce = Some(decode_hex(value)?),
            "body" => body = Some(decode_hex_vec(value)?),
            _ => return Err(VaultError::Malformed),
        }
    }
    let nonce_bytes = nonce.ok_or(VaultError::Malformed)?;
    if nonce_bytes.len() != 12 {
        return Err(VaultError::Malformed);
    }
    let mut nonce_array = [0u8; 12];
    nonce_array.copy_from_slice(&nonce_bytes);
    Ok(Record {
        mode: mode.ok_or(VaultError::Malformed)?,
        credential_id: credential_id.ok_or(VaultError::Malformed)?,
        key_id: key_id.ok_or(VaultError::Malformed)?,
        nonce: nonce_array,
        body: body.ok_or(VaultError::Malformed)?,
    })
}

struct Key([u8; 32]);

impl Key {
    fn bytes(&self) -> &[u8; 32] {
        &self.0
    }
}

impl Drop for Key {
    fn drop(&mut self) {
        wipe(&mut self.0);
    }
}

impl fmt::Debug for Key {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("Key(redacted)")
    }
}

fn load_key(path: &Path) -> Result<Key, VaultError> {
    let mut bytes = fs::read(path).map_err(|_| VaultError::Key)?;
    let parsed = key_from_bytes(&bytes);
    wipe(&mut bytes);
    parsed
}

fn key_from_bytes(bytes: &[u8]) -> Result<Key, VaultError> {
    if bytes.len() == 32 {
        let mut key = [0u8; 32];
        key.copy_from_slice(bytes);
        return Ok(Key(key));
    }
    let text = std::str::from_utf8(bytes).map_err(|_| VaultError::Key)?;
    let mut decoded = decode_hex_vec(text.trim()).map_err(|_| VaultError::Key)?;
    if decoded.len() != 32 {
        wipe(&mut decoded);
        return Err(VaultError::Key);
    }
    let mut key = [0u8; 32];
    key.copy_from_slice(&decoded);
    wipe(&mut decoded);
    Ok(Key(key))
}

fn encode_hex(bytes: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        out.push(HEX[(byte >> 4) as usize] as char);
        out.push(HEX[(byte & 0x0f) as usize] as char);
    }
    out
}

fn decode_hex(text: &str) -> Result<Vec<u8>, VaultError> {
    decode_hex_vec(text)
}

fn decode_hex_vec(text: &str) -> Result<Vec<u8>, VaultError> {
    if !text.len().is_multiple_of(2) {
        return Err(VaultError::Malformed);
    }
    let mut out = Vec::with_capacity(text.len() / 2);
    let bytes = text.as_bytes();
    let mut index = 0;
    while index < bytes.len() {
        let high = hex_value(bytes[index])?;
        let low = hex_value(bytes[index + 1])?;
        out.push((high << 4) | low);
        index += 2;
    }
    Ok(out)
}

fn hex_value(byte: u8) -> Result<u8, VaultError> {
    match byte {
        b'0'..=b'9' => Ok(byte - b'0'),
        b'a'..=b'f' => Ok(byte - b'a' + 10),
        b'A'..=b'F' => Ok(byte - b'A' + 10),
        _ => Err(VaultError::Malformed),
    }
}

impl Secret {
    fn login_str(&self) -> &str {
        std::str::from_utf8(&self.login).unwrap_or("")
    }

    fn password_str(&self) -> &str {
        std::str::from_utf8(&self.password).unwrap_or("")
    }

    fn server_str(&self) -> &str {
        std::str::from_utf8(&self.server).unwrap_or("")
    }
}

fn wipe(bytes: &mut [u8]) {
    for byte in bytes.iter_mut() {
        unsafe { std::ptr::write_volatile(byte, 0) }
    }
    std::sync::atomic::compiler_fence(std::sync::atomic::Ordering::SeqCst);
}

fn wipe_vec(mut bytes: Vec<u8>) {
    wipe(&mut bytes);
}

fn wipe_owned(mut bytes: Vec<u8>) {
    wipe(&mut bytes);
}

#[cfg(test)]
mod tests {
    use std::fs;
    use std::time::{SystemTime, UNIX_EPOCH};

    use super::{inject_at_startup, load_key, rotate_text, seal_text, Material, VaultError};

    fn key(seed: u8) -> [u8; 32] {
        [seed; 32]
    }

    fn nonce(seed: u8) -> [u8; 12] {
        [seed; 12]
    }

    #[test]
    fn a_sealed_file_round_trips_without_storing_the_password() {
        let text = seal_text(&key(1), &sim("exness-sim", "key-1"), &nonce(2)).unwrap();
        assert!(!text.contains("s3cret-value"));
        assert!(!text.contains("10001"));
        let dir = std::env::temp_dir().join(format!("sate-vault-{}", unique()));
        fs::create_dir_all(&dir).unwrap();
        let key_path = dir.join("key");
        let vault_path = dir.join("vault");
        fs::write(&key_path, key(1)).unwrap();
        fs::write(&vault_path, &text).unwrap();
        let audit = inject_at_startup(&key_path, &vault_path, "SIM", "").unwrap();
        assert_eq!(audit.action, "inject");
        assert_eq!(audit.credential_id, "exness-sim");
        assert_eq!(audit.key_id, "key-1");
        assert_eq!(audit.mode, "SIM");
        assert!(!audit.contains("s3cret-value"));
        assert!(!audit.contains("10001"));
        assert_eq!(load_key(&key_path).unwrap().bytes(), &key(1));
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn live_material_is_refused_on_a_sim_kernel_and_k3_stays_sealed() {
        let text = seal_text(&key(3), &live(), &nonce(4)).unwrap();
        let dir = std::env::temp_dir().join(format!("sate-vault-live-{}", unique()));
        fs::create_dir_all(&dir).unwrap();
        let key_path = dir.join("key");
        let vault_path = dir.join("vault");
        fs::write(&key_path, key(3)).unwrap();
        fs::write(&vault_path, &text).unwrap();
        assert_eq!(inject_at_startup(&key_path, &vault_path, "SIM", "").unwrap_err(), VaultError::LiveOnSim);
        assert_eq!(inject_at_startup(&key_path, &vault_path, "LIVE-L1", "").unwrap().mode, "LIVE");
        assert_eq!(inject_at_startup(&key_path, &vault_path, "LIVE-L1", "K3").unwrap_err(), VaultError::Sealed);
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn rotation_reseals_under_the_new_key_and_the_audit_has_no_secret() {
        let original = seal_text(&key(5), &sim("exness-sim", "key-old"), &nonce(6)).unwrap();
        let (rotated, audit) = rotate_text(&key(5), &key(9), "key-new", &original, "SIM", &nonce(7)).unwrap();
        assert_eq!(audit.action, "rotate");
        assert_eq!(audit.previous_key_id, "key-old");
        assert_eq!(audit.key_id, "key-new");
        assert!(!audit.contains("s3cret-value"));
        assert!(!rotated.contains("s3cret-value"));
        let dir = std::env::temp_dir().join(format!("sate-vault-rot-{}", unique()));
        fs::create_dir_all(&dir).unwrap();
        let key_path = dir.join("key");
        let vault_path = dir.join("vault");
        fs::write(&key_path, key(9)).unwrap();
        fs::write(&vault_path, &rotated).unwrap();
        assert_eq!(inject_at_startup(&key_path, &vault_path, "SIM", "").unwrap().key_id, "key-new");
        fs::write(&key_path, key(5)).unwrap();
        assert_eq!(inject_at_startup(&key_path, &vault_path, "SIM", "").unwrap_err(), VaultError::Crypto);
        let repeated = rotate_text(&key(9), &key(9), "key-again", &rotated, "SIM", &nonce(7));
        assert_eq!(repeated.unwrap_err(), VaultError::Crypto);
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn relabeling_a_live_vault_as_sim_does_not_open_it() {
        let text = seal_text(&key(3), &live(), &nonce(4)).unwrap();
        let relabeled = text.replace("mode LIVE", "mode SIM");
        let dir = std::env::temp_dir().join(format!("sate-vault-label-{}", unique()));
        fs::create_dir_all(&dir).unwrap();
        let key_path = dir.join("key");
        let vault_path = dir.join("vault");
        fs::write(&key_path, key(3)).unwrap();
        fs::write(&vault_path, relabeled).unwrap();
        let err = inject_at_startup(&key_path, &vault_path, "SIM", "").unwrap_err();
        assert_eq!(err, VaultError::Crypto);
        assert!(!err.to_string().contains("live-secret"));
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn a_label_that_repeats_the_password_is_refused() {
        let err = seal_text(&key(1), &sim("s3cret-value", "key-1"), &nonce(1));
        assert_eq!(err.unwrap_err(), VaultError::Secret);
    }

    fn sim<'a>(credential_id: &'a str, key_id: &'a str) -> Material<'a> {
        Material {
            mode: "SIM",
            credential_id,
            key_id,
            login: "10001",
            password: "s3cret-value",
            server: "Exness-MT5Trial",
        }
    }

    fn live() -> Material<'static> {
        Material {
            mode: "LIVE",
            credential_id: "exness-live",
            key_id: "key-live",
            login: "20002",
            password: "live-secret",
            server: "Exness-Real",
        }
    }

    fn unique() -> u128 {
        SystemTime::now().duration_since(UNIX_EPOCH).map(|item| item.as_nanos()).unwrap_or(0)
    }
}
