"""Mode-agnostic strategy engine **A-MOD-01**."""

from __future__ import annotations

from dataclasses import dataclass

from sate_strategy_a.black_litterman import blend_views
from sate_strategy_a.intent import build_intent
from sate_strategy_a.kalman import KalmanTickFilter
from sate_strategy_a.pre_kernel import MarketContext, validate_pre_kernel
from sate_strategy_a.regime import RegimeFilter
from sate_strategy_a.regime_online import OnlineRegime
from sate_strategy_a.sizing import size_position
from sate_strategy_a.universe import validate_instrument


@dataclass(frozen=True)
class StrategyDecision:
    abstain: bool
    intent: dict[str, object] | None
    reason: str = ""


@dataclass
class StrategyEngine:
    account_mode: str
    rung: str
    kalman: KalmanTickFilter
    regime: RegimeFilter
    online_regime: OnlineRegime | None = None
    strategy_id: str = "group-a-quant-v1"

    def evaluate_tick(
        self,
        *,
        intent_id: str,
        instrument: str,
        price: float,
        bid: str,
        advisory_view: float | None,
        sizing_inputs: dict[str, str],
        created_at: str,
        market_context: MarketContext | None = None,
    ) -> StrategyDecision:
        validate_instrument(instrument, account_mode=self.account_mode, rung=self.rung)
        signal = self.kalman.update(price)
        stable = not signal.triggered or signal.sigma < 3.0
        if self.online_regime is not None:
            stable = stable and self.online_regime.observe(price)
        self.regime.record(stable=stable)
        if self.regime.should_abstain():
            return StrategyDecision(abstain=True, intent=None, reason="regime_unstable")
        blend = blend_views(
            kalman_direction=signal.direction,
            advisory_view=advisory_view,
            regime_tilt=self.regime.tilt_enabled(),
        )
        if blend.view == 0.0 or not signal.triggered:
            return StrategyDecision(abstain=True, intent=None, reason="no_signal")
        side = "BUY" if blend.view > 0 else "SELL"
        sized = size_position(**sizing_inputs)
        if sized.rejected:
            return StrategyDecision(abstain=True, intent=None, reason=sized.reason)
        bid_f = float(bid)
        stop = f"{bid_f - 0.0050:.4f}" if side == "BUY" else f"{bid_f + 0.0050:.4f}"
        intent = build_intent(
            intent_id=intent_id,
            account_mode=self.account_mode,
            instrument=instrument,
            side=side,
            quantity=sized.quantity,
            protective_stop=stop,
            strategy_id=self.strategy_id,
            created_at=created_at,
            signal_refs=[blend.signal_ref],
            advisory_refs=["advisory-1"] if blend.advisory_used else [],
        )
        if market_context is not None:
            blocked = validate_pre_kernel(intent, context=market_context)
            if blocked is not None:
                return StrategyDecision(abstain=True, intent=None, reason=blocked.reason)
        return StrategyDecision(abstain=False, intent=intent)
