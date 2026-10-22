# KERNEL-A release

The production path runs a kernel only when the build identity has signed that exact binary and the deploy identity has authorized the install. The constitution key signs the constitution. It does not sign the kernel, and the build key does not authorize a deploy. The three public keys are pinned. Private keys are generated in memory for a ceremony and are not stored in this repo.

A candidate is staged only after the frozen `phase-8` red-team suite passes on those bytes. The fact log stores the suite version and the three results, bound to that binary hash. A missing or partial result does not activate. Staging does not make the artifact active. Activation needs a separate deploy authorization for that binary hash, git SHA, and constitution hash. The authorization also carries the change id, the reason, and the caller-supplied safety domains. The revision is the git SHA. The domains are stored and not interpreted. The kernel process refuses to start unless that deploy authorization is present and matches the signed binary.

Rollback authorizes the previous signed artifact and runs the same suite again. The fact log records the start and finish. The staging drill completes inside 15 minutes. There is no path that copies a binary into place.

## Key ceremony

Generation. Create the build key pair and the deploy key pair in memory. Pin each public key and key id in `config/staging.json`. Sign the manifest with the build key and the install authorization with the deploy key. Discard both private keys. The constitution pin stays `owner-key-1` and is not reused for either signature.

Rotation. Publish a new build public key, revoke the previous build key id, and record the rotation on the fact log. An artifact signed by the revoked key does not stage. The new key is the pin until the next rotation.

Revocation. A suspected compromise revokes the pinned build key and sets the required action to K3 plus re-provision. Stage, activate, and rollback stay closed until a rotation installs a new build key. This package records that requirement. It does not execute the kill.

A-DEC-07 stays open, so this service does not place KERNEL-A or MT5 in compose. The committed example signs a stub file, not a production binary. LIVE stays closed while the constitution lock hours are still the placeholder.
