"""
core/risk/stress_test.py
========================
Deterministic stress testing across predefined scenarios.

Scenarios:
- Crypto winter (BTC -60%, ETH -75%, alts -85%)
- Moderate correction (BTC -30%, ETH -40%)
- USD shock (DXY +15%)
- Rate spike (10Y +200bps — impacts RE valuation)
- Black swan (all risk assets -50%)

Each scenario applies shocks to liquid positions and estimates portfolio impact.
Illiquid positions get a separate liquidity risk flag — they can't be sold.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from .concentration import load_config


# Predefined shock scenarios
SCENARIOS = {
    "crypto_winter": {
        "description": "Prolonged crypto bear market — BTC -60%, ETH -75%, alts -85%",
        "shocks": {
            "crypto": -0.75,          # Default for crypto
            "BTC": -0.60,
            "ETH": -0.75,
            "crypto_equity": -0.50,   # Private equity marked down less
        },
    },
    "moderate_correction": {
        "description": "Mid-cycle correction — BTC -30%, broader risk-off",
        "shocks": {
            "crypto": -0.40,
            "BTC": -0.30,
            "ETH": -0.40,
            "crypto_equity": -0.20,
        },
    },
    "black_swan": {
        "description": "Systemic crisis — all risk assets -50%",
        "shocks": {
            "crypto": -0.50,
            "BTC": -0.50,
            "ETH": -0.50,
            "crypto_equity": -0.60,
            "public_equity": -0.40,
        },
    },
    "rate_spike": {
        "description": "Fed hikes aggressively — real estate cap rate expansion",
        "shocks": {
            "real_estate": -0.15,     # Cap rate expansion impact
            "crypto": -0.20,          # Risk-off spillover
        },
    },
}


@dataclass
class ScenarioResult:
    scenario_name: str
    description: str
    portfolio_loss_usd: float
    portfolio_loss_pct: float
    position_impacts: list[dict]
    illiquid_locked_usd: float        # Value you CAN'T sell
    liquid_remaining_usd: float       # Liquid value after shock
    alerts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "scenario": self.scenario_name,
            "description": self.description,
            "portfolio_loss_usd": round(self.portfolio_loss_usd, 2),
            "portfolio_loss_pct": round(self.portfolio_loss_pct, 4),
            "liquid_remaining_usd": round(self.liquid_remaining_usd, 2),
            "illiquid_locked_usd": round(self.illiquid_locked_usd, 2),
            "position_impacts": self.position_impacts,
            "alerts": self.alerts,
        }


def run_stress_test(
    positions_with_values: list[dict],   # Output from concentration.run_concentration_analysis
    total_portfolio_usd: float,
    scenario_names: Optional[list[str]] = None,
    config: Optional[dict] = None,
) -> list[ScenarioResult]:
    """
    Run one or more stress scenarios against current portfolio.

    Args:
        positions_with_values: Enriched positions list from ConcentrationReport.
        total_portfolio_usd: Current total portfolio value.
        scenario_names: Which scenarios to run. If None, runs all.
        config: Portfolio config. If None, loads from file.

    Returns:
        List of ScenarioResult, one per scenario.
    """
    if config is None:
        config = load_config()

    scenarios_to_run = scenario_names or list(SCENARIOS.keys())
    results = []

    for scenario_name in scenarios_to_run:
        if scenario_name not in SCENARIOS:
            continue

        scenario = SCENARIOS[scenario_name]
        shocks = scenario["shocks"]

        position_impacts = []
        total_loss = 0.0
        illiquid_locked = 0.0

        for pos in positions_with_values:
            value = pos["market_value_usd"]
            category = pos["category"]
            ticker = pos.get("id", "")
            liquidity = pos["liquidity"]

            # Determine shock: ticker-specific > category > 0
            shock_pct = shocks.get(ticker, shocks.get(category, 0.0))

            loss = value * shock_pct  # shock_pct is negative
            new_value = value + loss

            if liquidity == "illiquid":
                illiquid_locked += new_value

            position_impacts.append({
                "id": pos["id"],
                "name": pos["name"],
                "current_value": round(value, 2),
                "shock_applied_pct": shock_pct,
                "estimated_loss_usd": round(loss, 2),
                "post_shock_value": round(new_value, 2),
                "liquidity": liquidity,
            })
            total_loss += loss

        liquid_remaining = (total_portfolio_usd + total_loss) - illiquid_locked

        alerts = []
        if liquid_remaining < config["thresholds"].get("min_cash_buffer_usd", 50000):
            alerts.append(
                f"CRITICAL: Liquid holdings drop below minimum cash buffer "
                f"(${liquid_remaining:,.0f} remaining)"
            )
        loss_pct = total_loss / total_portfolio_usd if total_portfolio_usd else 0

        results.append(ScenarioResult(
            scenario_name=scenario_name,
            description=scenario["description"],
            portfolio_loss_usd=total_loss,
            portfolio_loss_pct=loss_pct,
            position_impacts=position_impacts,
            illiquid_locked_usd=illiquid_locked,
            liquid_remaining_usd=max(0, liquid_remaining),
            alerts=alerts,
        ))

    return results


if __name__ == "__main__":
    import json
    from .concentration import run_concentration_analysis

    sample_prices = {"BTC": 85000, "ETH": 3200}
    conc = run_concentration_analysis(prices=sample_prices)
    results = run_stress_test(
        positions_with_values=conc.positions,
        total_portfolio_usd=conc.total_portfolio_usd,
    )
    for r in results:
        print(json.dumps(r.to_dict(), indent=2))
