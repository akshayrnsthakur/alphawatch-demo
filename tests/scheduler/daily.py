"""
scheduler/daily.py
==================
Daily monitoring job. Runs every morning.

Tasks:
1. Fetch live prices → run concentration analysis
2. Fetch macro snapshot (FRED)
3. Fetch news snapshot
4. Check thresholds → fire anomaly alerts if breached
5. Generate daily macro synthesis via Claude

Run locally: python scheduler/daily.py
Production: AWS Lambda triggered by EventBridge (cron)
"""

from __future__ import annotations
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parents[1]))

from core.risk.concentration import run_concentration_analysis, load_config
from core.monitoring.macro import fetch_macro_snapshot
from core.monitoring.news import fetch_news
from core.monitoring.portfolio_tracker import fetch_all_prices
from ai.analyst import AlphaWatchAnalyst

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run_daily():
    logger.info("=== AlphaWatch Daily Run ===")
    config = load_config()
    analyst = AlphaWatchAnalyst()

    # 1. Prices
    crypto_tickers = [
        p["ticker"] for p in config["positions"]
        if p.get("ticker") and p["category"] == "crypto"
    ]
    logger.info(f"Fetching prices for: {crypto_tickers}")
    price_snapshot = fetch_all_prices(crypto_tickers=crypto_tickers)
    logger.info(f"Prices: {price_snapshot.prices}")

    # 2. Concentration
    conc_report = run_concentration_analysis(
        prices=price_snapshot.prices,
        config=config,
    )
    if conc_report.alerts:
        logger.warning(f"CONCENTRATION ALERTS: {conc_report.alerts}")

    # 3. Macro
    try:
        macro = fetch_macro_snapshot(
            indicator_ids=config["monitoring"]["macro_indicators"]
        )
        logger.info(f"Macro fetched: {len(macro.indicators)} indicators")
    except Exception as e:
        logger.error(f"Macro fetch failed: {e}")
        macro = None

    # 4. News
    news = fetch_news(config=config)
    logger.info(f"News fetched: {len(news.articles)} articles")

    # 5. Daily macro synthesis
    if macro:
        synthesis = analyst.synthesize_macro(
            macro_snapshot=macro.to_dict(),
            news_snapshot=news.to_dict(),
        )
        logger.info("Daily macro synthesis generated")
        print("\n" + synthesis)

    logger.info("=== Daily Run Complete ===")


if __name__ == "__main__":
    run_daily()
