//! Build-signature gate for the KERNEL-A binary. The deploy authorization is separate.

use ed25519_dalek::{Signature, Verifier, VerifyingKey};
use sha2::{Digest, Sha256};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Refuse {
    Unsigned,
    Signature,
    KeyId,
    Scope,
    Tamper,
    Downgrade,
    Version,
    ConstitutionHash,
    Provenance,
    Change,
    Malformed,
}

impl std::fmt::Display for Refuse {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let text = match self {
            Self::Unsigned => "kernel artifact is unsigned",
            Self::Signature => "kernel artifact signature is invalid",
            Self::KeyId => "build key id is not pinned",
            Self::Scope => "build, deploy, and constitution keys must stay distinct",
            Self::Change => "a deploy needs a change record",
            Self::Tamper => "kernel binary does not match the signed artifact",
            Self::Downgrade => "constitution version is downgraded",
            Self::Version => "constitution version is not pinned",
            Self::ConstitutionHash => "constitution hash does not match the pin",
            Self::Provenance => "git sha is not provenance",
            Self::Malformed => "kernel artifact is malformed",
        };
        formatter.write_str(text)
    }
}

/// Refuse a kernel whose bytes, signature, or constitution pin do not match.
pub fn accept(
    envelope_json: &str,
    binary: &[u8],
    build_public_hex: &str,
    build_key_id: &str,
    constitution_key_id: &str,
    expected_version: u64,
    constitution_hash: &str,
) -> Result<(), Refuse> {
    let value: serde_json::Value = serde_json::from_str(envelope_json).map_err(|_| Refuse::Malformed)?;
    let signature = value.get("signature").and_then(|item| item.as_str()).unwrap_or("");
    if signature.is_empty() {
        return Err(Refuse::Unsigned);
    }
    let key_id = value.get("key_id").and_then(|item| item.as_str()).unwrap_or("");
    if key_id == constitution_key_id {
        return Err(Refuse::Scope);
    }
    if key_id != build_key_id {
        return Err(Refuse::KeyId);
    }
    let canonical = text(&value, "canonical")?;
    let payload_hash = text(&value, "payload_hash")?;
    if sha256_hex(canonical.as_bytes()) != payload_hash {
        return Err(Refuse::Signature);
    }
    if !signature_valid(build_public_hex, canonical.as_bytes(), signature) {
        return Err(Refuse::Signature);
    }
    let manifest: serde_json::Value = serde_json::from_str(canonical).map_err(|_| Refuse::Malformed)?;
    if text(&manifest, "artifact_id")? != "kernel-a" || text(&manifest, "group_id")? != "A" {
        return Err(Refuse::Malformed);
    }
    let git_sha = text(&manifest, "git_sha")?;
    let git_sha_ok = git_sha.len() == 40
        && git_sha
            .chars()
            .all(|item| item.is_ascii_hexdigit() && !item.is_ascii_uppercase());
    if !git_sha_ok {
        return Err(Refuse::Provenance);
    }
    if text(&manifest, "binary_sha256")? != sha256_hex(binary) {
        return Err(Refuse::Tamper);
    }
    let version = manifest
        .get("constitution_version")
        .and_then(|item| item.as_u64())
        .ok_or(Refuse::Malformed)?;
    if version < expected_version {
        return Err(Refuse::Downgrade);
    }
    if version != expected_version {
        return Err(Refuse::Version);
    }
    if text(&manifest, "constitution_hash")? != constitution_hash {
        return Err(Refuse::ConstitutionHash);
    }
    Ok(())
}

/// The install authorization is a second signature. The build key cannot supply it.
pub fn authorize(
    authorization_json: &str,
    manifest_json: &str,
    deploy_public_hex: &str,
    deploy_key_id: &str,
    build_key_id: &str,
    constitution_key_id: &str,
) -> Result<(), Refuse> {
    if deploy_key_id == build_key_id || deploy_key_id == constitution_key_id || build_key_id == constitution_key_id {
        return Err(Refuse::Scope);
    }
    let value: serde_json::Value = serde_json::from_str(authorization_json).map_err(|_| Refuse::Malformed)?;
    let signature = value.get("signature").and_then(|item| item.as_str()).unwrap_or("");
    if signature.is_empty() {
        return Err(Refuse::Unsigned);
    }
    let key_id = value.get("key_id").and_then(|item| item.as_str()).unwrap_or("");
    if key_id != deploy_key_id {
        return Err(Refuse::KeyId);
    }
    let canonical = text(&value, "canonical")?;
    let payload_hash = text(&value, "payload_hash")?;
    if sha256_hex(canonical.as_bytes()) != payload_hash {
        return Err(Refuse::Signature);
    }
    if !signature_valid(deploy_public_hex, canonical.as_bytes(), signature) {
        return Err(Refuse::Signature);
    }
    let body: serde_json::Value = serde_json::from_str(canonical).map_err(|_| Refuse::Malformed)?;
    let action = text(&body, "action")?;
    if action != "activate" && action != "rollback" {
        return Err(Refuse::Malformed);
    }
    if !filled(body.get("change_id")) || !filled(body.get("reason")) || !domains_ok(body.get("safety_domains")) {
        return Err(Refuse::Change);
    }
    let manifest: serde_json::Value = serde_json::from_str(manifest_json).map_err(|_| Refuse::Malformed)?;
    let signed = manifest.get("canonical").ok_or(Refuse::Malformed)?;
    let manifest_body: serde_json::Value = match signed.as_str() {
        Some(text) => serde_json::from_str(text).map_err(|_| Refuse::Malformed)?,
        None => return Err(Refuse::Malformed),
    };
    for field in ["git_sha", "constitution_hash", "binary_sha256"] {
        if text(&body, field)? != text(&manifest_body, field)? {
            return Err(Refuse::Malformed);
        }
    }
    let authorized = body.get("constitution_version").and_then(|item| item.as_u64());
    let built = manifest_body.get("constitution_version").and_then(|item| item.as_u64());
    if authorized.is_none() || authorized != built {
        return Err(Refuse::Malformed);
    }
    Ok(())
}

fn filled(value: Option<&serde_json::Value>) -> bool {
    value.and_then(|item| item.as_str()).is_some_and(|text| !text.trim().is_empty())
}

fn domains_ok(value: Option<&serde_json::Value>) -> bool {
    let Some(items) = value.and_then(|item| item.as_array()) else {
        return false;
    };
    !items.is_empty() && items.iter().all(|item| item.as_str().is_some_and(|text| !text.trim().is_empty()))
}

pub fn sha256_hex(message: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let digest = Sha256::digest(message);
    let mut text = String::with_capacity(digest.len() * 2);
    for byte in digest {
        text.push(HEX[(byte >> 4) as usize] as char);
        text.push(HEX[(byte & 0x0f) as usize] as char);
    }
    text
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
    if !text.len().is_multiple_of(2) {
        return Err(Refuse::Malformed);
    }
    (0..text.len())
        .step_by(2)
        .map(|index| u8::from_str_radix(&text[index..index + 2], 16).map_err(|_| Refuse::Malformed))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::{Refuse, accept, authorize};

    fn pins() -> serde_json::Value {
        serde_json::from_str(include_str!("../../../release/config/staging.json")).unwrap()
    }

    #[test]
    fn the_staging_stub_matches_its_build_signature() {
        let pin = pins();
        accept(
            include_str!("../../../release/example/staging.manifest.json"),
            include_bytes!("../../../release/example/kernel-a.stub"),
            pin["build_public_key_hex"].as_str().unwrap(),
            pin["build_key_id"].as_str().unwrap(),
            pin["constitution_key_id"].as_str().unwrap(),
            pin["constitution_version"].as_u64().unwrap(),
            pin["constitution_hash"].as_str().unwrap(),
        )
        .unwrap();
    }

    #[test]
    fn a_tampered_stub_and_an_empty_signature_are_refused() {
        let pin = pins();
        let mut binary = include_bytes!("../../../release/example/kernel-a.stub").to_vec();
        binary.push(0);
        let tampered = accept(
            include_str!("../../../release/example/staging.manifest.json"),
            &binary,
            pin["build_public_key_hex"].as_str().unwrap(),
            pin["build_key_id"].as_str().unwrap(),
            pin["constitution_key_id"].as_str().unwrap(),
            pin["constitution_version"].as_u64().unwrap(),
            pin["constitution_hash"].as_str().unwrap(),
        );
        assert_eq!(tampered, Err(Refuse::Tamper));
        let mut envelope: serde_json::Value =
            serde_json::from_str(include_str!("../../../release/example/staging.manifest.json")).unwrap();
        envelope["signature"] = serde_json::Value::String(String::new());
        let unsigned = accept(
            &envelope.to_string(),
            include_bytes!("../../../release/example/kernel-a.stub"),
            pin["build_public_key_hex"].as_str().unwrap(),
            pin["build_key_id"].as_str().unwrap(),
            pin["constitution_key_id"].as_str().unwrap(),
            pin["constitution_version"].as_u64().unwrap(),
            pin["constitution_hash"].as_str().unwrap(),
        );
        assert_eq!(unsigned, Err(Refuse::Unsigned));
    }

    #[test]
    fn the_staging_authorization_matches_the_stub() {
        let pin = pins();
        authorize(
            include_str!("../../../release/example/staging.authorization.json"),
            include_str!("../../../release/example/staging.manifest.json"),
            pin["deploy_public_key_hex"].as_str().unwrap(),
            pin["deploy_key_id"].as_str().unwrap(),
            pin["build_key_id"].as_str().unwrap(),
            pin["constitution_key_id"].as_str().unwrap(),
        )
        .unwrap();
    }
}
