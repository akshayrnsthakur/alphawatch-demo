"""Tests for concentration risk analysis."""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from core.risk.concentration import run_concentration_analysis

SAMPLE_CONFIG = {
    "positions": [
        {"id": "BTC", "name": "Bitcoin", "ticker": "BTC", "category": "crypto",
         "liquidity": "liquid", "allocation_pct": 0.30, "cost_basis_usd": 50000},
        {"id": "ETH", "name": "Ethereum", "ticker": "ETH", "category": "crypto",
         "liquidity": "liquid", "allocation_pct": 0.20, "cost_basis_usd": 20000},
        {"id": "BITGO_EQUITY", "name": "BitGo Equity", "ticker": None,
         "category": "crypto_equity", "liquidity": "semi_liquid", "allocation_pct": 0.12},
        {"id": "RE_HYD", "name": "Hyderabad RE", "ticker": None,
         "category": "real_estate", "liquidity": "illiquid",
         "allocation_pct": 0.38, "valuation_usd": 190000},
    ],
    "thresholds": {
        "max_single_asset_pct": 0.35,
        "max_crypto_correlated_pct": 0.70,
        "max_illiquid_pct": 0.50,
        "min_cash_buffer_usd": 50000,
    },
}


def test_concentration_runs():
    report = run_concentration_analysis(prices={"BTC": 85000, "ETH": 3200}, config=SAMPLE_CONFIG)
    assert report.total_portfolio_usd > 0


def test_crypto_correlated_pct():
    report = run_concentration_analysis(prices={}, config=SAMPLE_CONFIG)
    # BTC (0.30) + ETH (0.20) + BitGo equity (0.12) = 0.62 crypto-correlated
    assert 0.50 < report.crypto_correlated_pct < 0.75


def test_illiquid_pct():
    report = run_concentration_analysis(prices={}, config=SAMPLE_CONFIG)
    assert report.illiquid_pct > 0


def test_no_alerts_within_thresholds():
    """With default config, no alerts should fire at normal allocations."""
    report = run_concentration_analysis(prices={}, config=SAMPLE_CONFIG)
    # RE at 38% is under 50% illiquid threshold — no alert expected
    illiquid_alerts = [a for a in report.alerts if "ILLIQUIDITY" in a]
    assert len(illiquid_alerts) == 0


def test_to_dict():
    report = run_concentration_analysis(prices={}, config=SAMPLE_CONFIG)
    d = report.to_dict()
    assert "total_portfolio_usd" in d
    assert "crypto_correlated_pct" in d
    assert "alerts" in d
