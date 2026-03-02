"""
core/risk/hedging.py
====================
BTC options hedge sizing and coverage analysis.

Computes:
- Current hedge coverage vs target
- Recommended notional to hedge
- Put option sizing guidelines (Black-Scholes not used — deterministic rules only)

Does NOT execute trades. Outputs recommendations for human review.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from .concentration import load_config


@dataclass
class HedgeReport:
    btc_exposure_usd: float
    target_coverage_pct: float
    target_coverage_usd: float
    current_hedge_usd: float         # Pass in from your actual open positions
    coverage_gap_usd: float
    action_required: bool
    recommendation: str

    def to_dict(self) -> dict:
        return {
            "btc_exposure_usd": round(self.btc_exposure_usd, 2),
            "target_coverage_usd": round(self.target_coverage_usd, 2),
            "current_hedge_usd": round(self.current_hedge_usd, 2),
            "coverage_gap_usd": round(self.coverage_gap_usd, 2),
            "action_required": self.action_required,
            "recommendation": self.recommendation,
        }


def compute_hedge_sizing(
    positions_with_values: list[dict],
    current_hedge_usd: float = 0.0,
    config: Optional[dict] = None,
) -> HedgeReport:
    """
    Compute hedge sizing recommendation based on current BTC exposure.

    Args:
        positions_with_values: Enriched positions from ConcentrationReport.
        current_hedge_usd: Notional value of currently open put options.
        config: Portfolio config.

    Returns:
        HedgeReport with sizing recommendation.
    """
    if config is None:
        config = load_config()

    hedge_cfg = config.get("hedging", {})
    target_pct = hedge_cfg.get("target_coverage_pct", 0.20)
    rebalance_trigger = hedge_cfg.get("rebalance_trigger_pct", 0.05)

    # Find BTC position value
    btc_value = sum(
        p["market_value_usd"] for p in positions_with_values
        if p["id"] == "BTC"
    )

    target_usd = btc_value * target_pct
    gap = target_usd - current_hedge_usd
    gap_pct = abs(gap) / target_usd if target_usd else 0
    action_required = gap_pct > rebalance_trigger

    if not hedge_cfg.get("enabled", True):
        recommendation = "Hedging disabled in config."
    elif btc_value == 0:
        recommendation = "No BTC exposure detected. No hedge needed."
    elif action_required:
        if gap > 0:
            recommendation = (
                f"BUY ${gap:,.0f} notional in BTC put options to reach target coverage. "
                f"Consider 3-month 80% strike puts for downside protection."
            )
        else:
            recommendation = (
                f"REDUCE hedge by ${abs(gap):,.0f} notional — currently over-hedged."
            )
    else:
        recommendation = (
            f"Hedge coverage is within tolerance. No action needed. "
            f"(Coverage: ${current_hedge_usd:,.0f} / Target: ${target_usd:,.0f})"
        )

    return HedgeReport(
        btc_exposure_usd=btc_value,
        target_coverage_pct=target_pct,
        target_coverage_usd=target_usd,
        current_hedge_usd=current_hedge_usd,
        coverage_gap_usd=gap,
        action_required=action_required,
        recommendation=recommendation,
    )
