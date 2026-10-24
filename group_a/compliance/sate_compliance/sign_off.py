"""Owner written sign-off artifact."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OwnerSignOff:
    sign_off_id: str
    owner: str
    signed_at: str
    evidence_package_id: str
    attestation: str

    @property
    def present(self) -> bool:
        return bool(self.sign_off_id and self.signed_at and self.evidence_package_id)
