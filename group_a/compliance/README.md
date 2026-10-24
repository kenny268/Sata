# Group A broker compliance (Phase 24)

| ID | Module |
|----|--------|
| **A-P0-20** | `BrokerEvidencePackage` + schema |
| **INV-08** | Unknown rules stay disabled — `inv08_unknown_rules_disabled` preflight reason |
| **A-FEE-05** | `TaxReportingMemo` slot |
| **A-DEC-01/08/10** | `BlockerRecord` OPEN / BLOCKED / RESOLVED |
| **BAT** | `ProtectiveOrderBat` demo verification steps |
| **SEC** | `RelayPolicy` — disabled by default; must be fully configured if enabled |

LIVE arm (`/mode/A/arm`) builds the gate from the **fact log** via `broker_ops_wire.gate_for_arm` when compliance is on `PYTHONPATH`. Empty log → blocked. Tests may pass **`broker_verification_complete: true`** for the staging complete gate without persisting evidence.

Persist: `persist_evidence_package`, `persist_sign_off`, `persist_tax_memo`, `persist_blockers`, `persist_bat_verification` → writer **`compliance-a`**. `seed_staging_verification()` loads the staging complete package into a log.

Env:
- **`SATE_SEC_RELAY_*`** — relay enable path (**A-DEC-08**)
- **`SATE_BAT_PROTECTIVE_VERIFIED`** — operator BAT attestation without MT5
- **`SATE_BROKER_WRITTEN_VERIFICATION`** — §7.4 written packet on file
- **`SATE_COMPLIANCE_FACTLOG`** / **`SATE_PHASE24_REPORT_DIR`** — `phase24_runner`

MT5 BAT: `sate_mt5_bridge.bat.run_protective_order_bat` via `sate_compliance.mt5_bat.run_demo_protective_bat`.

Operator: flip **`kenya_exness_written_verification_on_file`** in `phase-24-tracker.json` when written §7.4 evidence is on file (mirrors `SATE_BROKER_WRITTEN_VERIFICATION`).
