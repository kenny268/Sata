"""Ed25519 seal for a constitution. The private key is not stored here."""

from __future__ import annotations

import hashlib

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from sate_constitution.document import canonical_bytes, validate_document
from sate_constitution.errors import ConstitutionError


def generate_keypair() -> tuple[bytes, bytes]:
    private = Ed25519PrivateKey.generate()
    secret = private.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    public = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return secret, public


def sign(private_key: bytes, message: bytes) -> bytes:
    return Ed25519PrivateKey.from_private_bytes(private_key).sign(message)


def verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(signature, message)
    except (InvalidSignature, ValueError):
        return False
    return True


def seal(
    document: dict[str, object],
    *,
    private_key: bytes,
    key_id: str,
    effective_at: str,
    expires_at: str,
) -> dict[str, object]:
    validate_document(document)
    if document["meta"]["signed_by"] != key_id:
        raise ConstitutionError("signed_by does not match the key id", code="key_id")
    if document["meta"]["group"] != "A" and document["meta"]["group"] != "B":
        raise ConstitutionError("constitution group is A or B", code="scope")
    canonical = canonical_bytes(document).decode()
    signature = sign(private_key, canonical.encode()).hex()
    return {
        "constitution_id": document["meta"]["constitution_id"],
        "group_id": document["meta"]["group"],
        "version": document["meta"]["version"],
        "effective_at": effective_at,
        "expires_at": expires_at,
        "key_id": key_id,
        "payload_hash": hashlib.sha256(canonical.encode()).hexdigest(),
        "signature": signature,
        "canonical": canonical,
        "document": document,
    }


def signature_valid(envelope: dict[str, object], public_key: bytes) -> bool:
    canonical = envelope.get("canonical")
    signature = envelope.get("signature")
    if not isinstance(canonical, str) or not isinstance(signature, str) or not signature:
        return False
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    if envelope.get("payload_hash") != digest:
        return False
    try:
        raw = bytes.fromhex(signature)
    except ValueError:
        return False
    return verify(public_key, canonical.encode(), raw)
