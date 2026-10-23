"""Pre-kernel validation before intent leaves strategy (**§5.2**, **§6.2**)."""

from __future__ import annotations

from dataclasses import dataclass

from sate_strategy_a.abstain import AbstainDecision, abstain
from sate_strategy_a.freshness import validate_freshness
from sate_strategy_a.fx_calendar import calendar_loaded_for
from sate_strategy_a.intent import validate_intent
from sate_strategy_a.overnight import reject_overnight_carry
from sate_strategy_a.swap_guard import check_swap_guard


@dataclass(frozen=True)
class MarketContext:
    tick_age_ms: int
    swap_estimate: float
    swap_budget: float
    hold_includes_wednesday: bool
    hold_through_close: bool
    constitution_overnight_ok: bool = False
    news_blackout: bool = False
    calendar_week: str = ""
    as_of: str = ""


def validate_pre_kernel(
    intent: dict[str, object],
    *,
    context: MarketContext,
) -> AbstainDecision | None:
    fresh = validate_freshness(age_ms=context.tick_age_ms)
    if not fresh.ok:
        return abstain(reason=fresh.reason, detail=f"age_ms={context.tick_age_ms}")
    if context.as_of and not calendar_loaded_for(context.as_of, context.calendar_week):
        return abstain(reason="calendar_stale", detail="A-EXE-02")
    if context.news_blackout:
        return abstain(reason="news_blackout", detail="A-EXE-02")
    if reject_overnight_carry(
        hold_through_close=context.hold_through_close,
        constitution_allows=context.constitution_overnight_ok,
    ):
        return abstain(reason="overnight_bias", detail="A-UNI-03 default flat")
    swap = check_swap_guard(
        estimated_swap=context.swap_estimate,
        swap_budget=context.swap_budget,
        hold_includes_wednesday=context.hold_includes_wednesday,
    )
    if not swap.allowed:
        return abstain(reason=swap.reason, detail="swap exceeds budget")
    validate_intent(intent)
    return None
