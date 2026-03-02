"""
scheduler/weekly.py
===================
Weekly intelligence brief generation. Runs Sunday mornings.

Tasks:
1. Full concentration analysis
2. All stress test scenarios
3. Hedge sizing check
4. Macro snapshot
5. News snapshot
6. Generate weekly brief via Claude

Run locally: python scheduler/weekly.py
Production: AWS Lambda triggered by EventBridge (cron: 0 8 * * 0)
"""

from __future__ import annotations
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from core.risk.concentration import run_concentration_analysis, load_config
from core.risk.stress_test import run_stress_test
from core.risk.hedging import compute_hedge_sizing
from core.monitoring.macro import fetch_macro_snapshot
from core.monitoring.news import fetch_news
from core.monitoring.portfolio_tracker import fetch_all_prices
from ai.analyst import AlphaWatchAnalyst

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run_weekly():
    logger.info("=== AlphaWatch Weekly Run ===")
    config = load_config()
    analyst = AlphaWatchAnalyst()

    # Prices
    crypto_tickers = [
        p["ticker"] for p in config["positions"]
        if p.get("ticker") and p["category"] == "crypto"
    ]
    price_snapshot = fetch_all_prices(crypto_tickers=crypto_tickers)

    # Concentration
    conc_report = run_concentration_analysis(prices=price_snapshot.prices, config=config)
    logger.info(f"Concentration: crypto={conc_report.crypto_correlated_pct:.1%} illiquid={conc_report.illiquid_pct:.1%}")

    # Stress tests
    stress_results = run_stress_test(
        positions_with_values=conc_report.positions,
        total_portfolio_usd=conc_report.total_portfolio_usd,
        config=config,
    )
    logger.info(f"Stress tests: {len(stress_results)} scenarios")

    # Hedge sizing
    hedge_report = compute_hedge_sizing(
        positions_with_values=conc_report.positions,
        config=config,
    )

    # Macro
    macro = fetch_macro_snapshot(
        indicator_ids=config["monitoring"]["macro_indicators"]
    )

    # News
    news = fetch_news(config=config)

    # Weekly brief
    brief = analyst.generate_weekly_brief(
        concentration_report=conc_report.to_dict(),
        stress_results=[r.to_dict() for r in stress_results],
        macro_snapshot=macro.to_dict(),
        news_snapshot=news.to_dict(),
        hedge_report=hedge_report.to_dict(),
    )

    print("\n" + "=" * 60)
    print(brief)
    print("=" * 60)
    logger.info("=== Weekly Run Complete ===")


if __name__ == "__main__":
    run_weekly()
