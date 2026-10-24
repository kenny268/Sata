"""Instrument pricing profile **A-UNI-02**."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PricingProfile:
    name: str
    spread_pips: float
    commission_per_lot: float


RAW_COMMISSION = PricingProfile(name="raw_commission", spread_pips=0.1, commission_per_lot=3.5)
WIDE_SPREAD = PricingProfile(name="wide_spread", spread_pips=1.5, commission_per_lot=0.0)


def prefer_raw_commission(*, profile: str) -> PricingProfile:
    if profile == "wide_spread":
        return WIDE_SPREAD
    return RAW_COMMISSION


def effective_spread_cost(profile: PricingProfile, *, lots: float) -> float:
    spread = profile.spread_pips * lots
    commission = profile.commission_per_lot * lots
    if profile.name == "raw_commission":
        return spread + commission
    return spread
