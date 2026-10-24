"""Phase 24 broker verification report."""

from __future__ import annotations

from sate_factlog.log import FactLog

from sate_compliance.broker_ops_wire import gate_for_arm, written_verification_on_file
from sate_compliance.fact_load import READER_ID, load_broker_state
from sate_compliance.relay_policy import relay_policy_from_env


def build_phase24_report(log: FactLog, *, as_of: str) -> dict[str, object]:
    gate = gate_for_arm(log, as_of=as_of)
    reasons = gate.block_reasons()
    state = load_broker_state(log, as_of=as_of, reader_id=READER_ID)
    relay = relay_policy_from_env()
    package_id = gate.package.package_id if gate.package else None
    return {
        "phase": 24,
        "as_of": as_of,
        "live_arm_allowed": not reasons,
        "block_reasons": reasons,
        "evidence_package_id": package_id,
        "sign_off_present": state.sign_off is not None and state.sign_off.present,
        "relay_enabled": relay.enabled,
        "relay_sec_ok": relay.sec_ok(),
        "bat_protective_ok": gate.bat_protective_ok,
        "operator_written_verification_on_file": written_verification_on_file(),
        "phase24_exit_met": not reasons and written_verification_on_file(),
    }
