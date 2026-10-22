//! Signed constitution gate. A trade has no separate approval step.

use ed25519_dalek::{Signature, Verifier, VerifyingKey};
use sha2::{Digest, Sha256};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Refuse {
    Unsigned,
    Signature,
    KeyId,
    Expired,
    NotYetEffective,
    Version,
    Malformed,
}

impl std::fmt::Display for Refuse {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let text = match self {
            Self::Unsigned => "constitution is unsigned",
            Self::Signature => "constitution signature is invalid",
            Self::KeyId => "constitution key id is not pinned",
            Self::Expired => "constitution has expired",
            Self::NotYetEffective => "constitution is not effective yet",
            Self::Version => "constitution version is not pinned",
            Self::Malformed => "constitution artifact is malformed",
        };
        formatter.write_str(text)
    }
}

/// Verify the pinned key, the signature, the effective window, and the version.
/// There is no per-trade approval argument.
pub fn accept(
    envelope_json: &str,
    pinned_key_hex: &str,
    pinned_key_id: &str,
    now: &str,
    expected_version: Option<u64>,
) -> Result<u64, Refuse> {
    let value: serde_json::Value =
        serde_json::from_str(envelope_json).map_err(|_| Refuse::Malformed)?;
    let signature = value.get("signature").and_then(|item| item.as_str()).unwrap_or("");
    if signature.is_empty() {
        return Err(Refuse::Unsigned);
    }
    let key_id = value.get("key_id").and_then(|item| item.as_str()).unwrap_or("");
    if key_id != pinned_key_id {
        return Err(Refuse::KeyId);
    }
    let canonical = text(&value, "canonical")?;
    let payload_hash = text(&value, "payload_hash")?;
    if sha256_hex(canonical.as_bytes()) != payload_hash {
        return Err(Refuse::Signature);
    }
    if !signature_valid(pinned_key_hex, canonical.as_bytes(), signature) {
        return Err(Refuse::Signature);
    }
    let effective = text(&value, "effective_at")?;
    let expires = text(&value, "expires_at")?;
    if now < effective {
        return Err(Refuse::NotYetEffective);
    }
    if now >= expires {
        return Err(Refuse::Expired);
    }
    let document: serde_json::Value =
        serde_json::from_str(canonical).map_err(|_| Refuse::Malformed)?;
    let version = document
        .get("meta")
        .and_then(|meta| meta.get("version"))
        .and_then(|item| item.as_u64())
        .ok_or(Refuse::Malformed)?;
    if expected_version.is_some_and(|expected| expected != version) {
        return Err(Refuse::Version);
    }
    Ok(version)
}

fn text<'a>(value: &'a serde_json::Value, key: &str) -> Result<&'a str, Refuse> {
    value.get(key).and_then(|item| item.as_str()).ok_or(Refuse::Malformed)
}

fn signature_valid(public_hex: &str, message: &[u8], signature_hex: &str) -> bool {
    let Ok(public) = decode_fixed::<32>(public_hex) else {
        return false;
    };
    let Ok(raw) = decode_fixed::<64>(signature_hex) else {
        return false;
    };
    let Ok(key) = VerifyingKey::from_bytes(&public) else {
        return false;
    };
    let Ok(signature) = Signature::from_slice(&raw) else {
        return false;
    };
    key.verify(message, &signature).is_ok()
}

fn decode_fixed<const N: usize>(text: &str) -> Result<[u8; N], Refuse> {
    let bytes = decode_hex(text)?;
    bytes.try_into().map_err(|_| Refuse::Malformed)
}

fn decode_hex(text: &str) -> Result<Vec<u8>, Refuse> {
    if text.len() % 2 != 0 {
        return Err(Refuse::Malformed);
    }
    (0..text.len())
        .step_by(2)
        .map(|index| u8::from_str_radix(&text[index..index + 2], 16).map_err(|_| Refuse::Malformed))
        .collect()
}

fn sha256_hex(message: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let digest = Sha256::digest(message);
    let mut text = String::with_capacity(digest.len() * 2);
    for byte in digest {
        text.push(HEX[(byte >> 4) as usize] as char);
        text.push(HEX[(byte & 0x0f) as usize] as char);
    }
    text
}

#[cfg(test)]
mod tests {
    use super::{Refuse, accept};

    const KEY: &str = "51fbb771cf44d972ed89312b2b6cd21cfde8dcf737795148cb87db1fd6639a01";
    const SIGNATURE: &str = "ea058195391dde56a017dff03113e31279a30f84a319246ffc938aa9354c7d64162eabc1f65bc12aea534922c55b288bebb4a58f4f700de2451773f63a99200a";
    const HASH: &str = "0efc2ae1a4db360a50e202df2f3e3b9a35681c0fa1904134da205ee1d3fbc704";

    fn envelope(signature: &str, expires: &str) -> String {
        serde_json::json!({
            "canonical": r#"{"meta":{"version":1}}"#,
            "effective_at": "2026-01-01T00:00:00Z",
            "expires_at": expires,
            "key_id": "owner-key-1",
            "payload_hash": HASH,
            "signature": signature,
        })
        .to_string()
    }

    #[test]
    fn a_pinned_signature_is_accepted() {
        let version = accept(
            &envelope(SIGNATURE, "2027-10-22T00:00:00Z"),
            KEY,
            "owner-key-1",
            "2026-10-22T00:00:00Z",
            Some(1),
        )
        .unwrap();
        assert_eq!(version, 1);
    }

    #[test]
    fn unsigned_expired_and_mismatched_versions_are_refused() {
        let missing = accept(
            &envelope("", "2027-10-22T00:00:00Z"),
            KEY,
            "owner-key-1",
            "2026-10-22T00:00:00Z",
            None,
        );
        assert_eq!(missing, Err(Refuse::Unsigned));
        let expired = accept(
            &envelope(SIGNATURE, "2026-02-01T00:00:00Z"),
            KEY,
            "owner-key-1",
            "2026-10-22T00:00:00Z",
            None,
        );
        assert_eq!(expired, Err(Refuse::Expired));
        let mismatched = accept(
            &envelope(SIGNATURE, "2027-10-22T00:00:00Z"),
            KEY,
            "owner-key-1",
            "2026-10-22T00:00:00Z",
            Some(2),
        );
        assert_eq!(mismatched, Err(Refuse::Version));
    }
}
