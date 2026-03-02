"""
core/risk/concentration.py
==========================
Deterministic concentration risk analysis.

Computes:
- Per-asset and per-category allocation percentages
- Crypto-correlated exposure (crypto + crypto_equity)
- Illiquid exposure
- Threshold breach alerts

No AI. Pure math. Every output is reproducible.
"""

from __future__ import annotations
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


CRYPTO_CORRELATED_CATEGORIES = {"crypto", "crypto_equity"}
ILLIQUID_CATEGORIES = {"illiquid"}
SEMI_LIQUID_CATEGORIES = {"semi_liquid"}


@dataclass
class ConcentrationReport:
    total_portfolio_usd: float
    positions: list[dict]
    category_breakdown: dict[str, float]        # category -> % of portfolio
    liquidity_breakdown: dict[str, float]        # liquidity -> % of portfolio
    crypto_correlated_pct: float
    illiquid_pct: float
    alerts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_portfolio_usd": self.total_portfolio_usd,
            "crypto_correlated_pct": round(self.crypto_correlated_pct, 4),
            "illiquid_pct": round(self.illiquid_pct, 4),
            "category_breakdown": {k: round(v, 4) for k, v in self.category_breakdown.items()},
            "liquidity_breakdown": {k: round(v, 4) for k, v in self.liquidity_breakdown.items()},
            "positions": self.positions,
            "alerts": self.alerts,
        }


def load_config(config_path: Optional[Path] = None) -> dict:
    if config_path is None:
        config_path = Path(__file__).parents[3] / "config" / "portfolio.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def run_concentration_analysis(
    prices: dict[str, float],  # {ticker: current_price_usd}
    config: Optional[dict] = None,
) -> ConcentrationReport:
    """
    Main entry point. Pass in live prices; returns full concentration report.

    Args:
        prices: Dict of ticker -> current USD price. Non-crypto positions
                should use their valuation_usd from config (pass ticker=None).
        config: Portfolio config dict. If None, loads from portfolio.yaml.

    Returns:
        ConcentrationReport with all metrics and threshold alerts.
    """
    if config is None:
        config = load_config()

    positions_cfg = config["positions"]
    thresholds = config["thresholds"]

    # --- Compute position market values ---
    enriched = []
    for pos in positions_cfg:
        ticker = pos.get("ticker")
        if ticker and ticker in prices:
            # Crypto/equity with live price — TODO: need quantity, not just allocation_pct
            # For now, use allocation_pct * total as placeholder until positions have quantity
            market_value = pos.get("allocation_pct", 0.0)  # placeholder
        else:
            # Real estate or unlisted — use manual valuation
            market_value = pos.get("valuation_usd", pos.get("allocation_pct", 0.0))

        enriched.append({
            "id": pos["id"],
            "name": pos["name"],
            "category": pos["category"],
            "liquidity": pos["liquidity"],
            "market_value_usd": market_value,
        })

    total = sum(p["market_value_usd"] for p in enriched) or 1  # avoid div/0

    # --- Compute percentages ---
    for pos in enriched:
        pos["pct_of_portfolio"] = round(pos["market_value_usd"] / total, 4)

    # --- Category breakdown ---
    category_breakdown: dict[str, float] = {}
    for pos in enriched:
        cat = pos["category"]
        category_breakdown[cat] = category_breakdown.get(cat, 0.0) + pos["pct_of_portfolio"]

    # --- Liquidity breakdown ---
    liquidity_breakdown: dict[str, float] = {}
    for pos in enriched:
        liq = pos["liquidity"]
        liquidity_breakdown[liq] = liquidity_breakdown.get(liq, 0.0) + pos["pct_of_portfolio"]

    # --- Derived metrics ---
    crypto_correlated_pct = sum(
        p["pct_of_portfolio"] for p in enriched
        if p["category"] in CRYPTO_CORRELATED_CATEGORIES
    )
    illiquid_pct = sum(
        p["pct_of_portfolio"] for p in enriched
        if p["liquidity"] in ILLIQUID_CATEGORIES
    )

    # --- Threshold alerts ---
    alerts = []
    for pos in enriched:
        if pos["pct_of_portfolio"] > thresholds["max_single_asset_pct"]:
            alerts.append(
                f"CONCENTRATION: {pos['id']} is {pos['pct_of_portfolio']:.1%} of portfolio "
                f"(threshold: {thresholds['max_single_asset_pct']:.1%})"
            )
    if crypto_correlated_pct > thresholds["max_crypto_correlated_pct"]:
        alerts.append(
            f"CRYPTO EXPOSURE: {crypto_correlated_pct:.1%} crypto-correlated "
            f"(threshold: {thresholds['max_crypto_correlated_pct']:.1%})"
        )
    if illiquid_pct > thresholds["max_illiquid_pct"]:
        alerts.append(
            f"ILLIQUIDITY: {illiquid_pct:.1%} of portfolio is illiquid "
            f"(threshold: {thresholds['max_illiquid_pct']:.1%})"
        )

    return ConcentrationReport(
        total_portfolio_usd=total,
        positions=enriched,
        category_breakdown=category_breakdown,
        liquidity_breakdown=liquidity_breakdown,
        crypto_correlated_pct=crypto_correlated_pct,
        illiquid_pct=illiquid_pct,
        alerts=alerts,
    )


if __name__ == "__main__":
    import json

    # Demo run with placeholder prices
    sample_prices = {
        "BTC": 85000,
        "ETH": 3200,
        "SOL": 180,
    }
    report = run_concentration_analysis(prices=sample_prices)
    print(json.dumps(report.to_dict(), indent=2))
