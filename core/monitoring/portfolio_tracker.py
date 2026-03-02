"""
core/monitoring/portfolio_tracker.py
=====================================
Live price feeds via CoinGecko (free tier) and Yahoo Finance.

Fetches:
- Crypto prices (CoinGecko)
- Public equity prices (Yahoo Finance via yfinance)
- Computes current portfolio value and P&L vs cost basis

Deterministic. No AI.
"""

from __future__ import annotations
import os
import requests
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


COINGECKO_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"

# Map your position tickers to CoinGecko IDs
COINGECKO_ID_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "AVAX": "avalanche-2",
    "MATIC": "matic-network",
    "LINK": "chainlink",
    "ARB": "arbitrum",
    "OP": "optimism",
}


@dataclass
class PriceSnapshot:
    fetched_at: str
    prices: dict[str, float]    # {ticker: usd_price}
    errors: list[str]

    def to_dict(self) -> dict:
        return {
            "fetched_at": self.fetched_at,
            "prices": self.prices,
            "errors": self.errors,
        }


def fetch_crypto_prices(tickers: list[str]) -> dict[str, float]:
    """Fetch USD prices for crypto tickers via CoinGecko free API."""
    ids = [COINGECKO_ID_MAP[t] for t in tickers if t in COINGECKO_ID_MAP]
    if not ids:
        return {}

    params = {
        "ids": ",".join(ids),
        "vs_currencies": "usd",
    }
    resp = requests.get(COINGECKO_PRICE_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    # Reverse map: CoinGecko ID -> ticker
    id_to_ticker = {v: k for k, v in COINGECKO_ID_MAP.items()}
    return {
        id_to_ticker[cg_id]: info["usd"]
        for cg_id, info in data.items()
        if cg_id in id_to_ticker
    }


def fetch_equity_prices(tickers: list[str]) -> dict[str, float]:
    """Fetch USD prices for public equities via yfinance."""
    if not YFINANCE_AVAILABLE or not tickers:
        return {}
    prices = {}
    for ticker in tickers:
        try:
            data = yf.Ticker(ticker).fast_info
            prices[ticker] = data.last_price
        except Exception:
            pass
    return prices


def fetch_all_prices(
    crypto_tickers: list[str],
    equity_tickers: Optional[list[str]] = None,
) -> PriceSnapshot:
    """
    Fetch all current prices. Returns PriceSnapshot with combined results.
    """
    prices = {}
    errors = []

    try:
        crypto_prices = fetch_crypto_prices(crypto_tickers)
        prices.update(crypto_prices)
    except Exception as e:
        errors.append(f"CoinGecko fetch failed: {e}")

    if equity_tickers:
        try:
            equity_prices = fetch_equity_prices(equity_tickers)
            prices.update(equity_prices)
        except Exception as e:
            errors.append(f"Yahoo Finance fetch failed: {e}")

    return PriceSnapshot(
        fetched_at=datetime.utcnow().isoformat(),
        prices=prices,
        errors=errors,
    )


if __name__ == "__main__":
    import json
    snapshot = fetch_all_prices(
        crypto_tickers=["BTC", "ETH", "SOL"],
        equity_tickers=["COIN", "MSTR"],
    )
    print(json.dumps(snapshot.to_dict(), indent=2))
