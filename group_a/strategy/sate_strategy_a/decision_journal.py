"""Decision journal before action (**A-PR-08**)."""

from __future__ import annotations

from sate_factlog.log import FactLog


def persist_decision_journal(
    log: FactLog,
    *,
    intent_id: str,
    hypothesis: str,
    action: str,
    at: str,
    advisory_inputs: str = "none",
    risks: str = "gap",
    expected_return: str = "0",
    expected_downside: str = "0",
    verdict_ref: str = "pending",
) -> None:
    log.append(
        event_id=f"journal-{intent_id}",
        event_type="journal",
        group_scope="A",
        occurred_at=at,
        recorded_at=at,
        correlation_id=intent_id,
        writer_id="strategy-a",
        payload={
            "as_of": at,
            "hypothesis": hypothesis,
            "advisory_inputs": advisory_inputs,
            "risks": risks,
            "expected_return": expected_return,
            "expected_downside": expected_downside,
            "action": action,
            "verdict_ref": verdict_ref,
        },
    )
