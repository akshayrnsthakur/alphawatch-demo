"""
core/monitoring/macro.py
========================
FRED API data fetcher for macro indicators.

Fetches configured macro indicators and returns structured snapshots
for Claude synthesis. All fetching is deterministic; interpretation is Claude's job.

FRED API is free — get key at fred.stlouisfed.org
"""

from __future__ import annotations
import os
import requests
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional


FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

INDICATOR_META = {
    "DFF":       {"name": "Fed Funds Rate",          "unit": "%"},
    "T10Y2Y":    {"name": "10Y-2Y Yield Spread",     "unit": "%"},
    "DTWEXBGS":  {"name": "USD Index (Broad)",        "unit": "index"},
    "CPIAUCSL":  {"name": "CPI (YoY proxy)",          "unit": "index"},
    "UNRATE":    {"name": "Unemployment Rate",        "unit": "%"},
    "VIXCLS":    {"name": "VIX",                      "unit": "index"},
    "T10YIE":    {"name": "10Y Breakeven Inflation",  "unit": "%"},
    "BAMLH0A0HYM2": {"name": "HY Credit Spread",     "unit": "bps"},
}


@dataclass
class MacroSnapshot:
    fetched_at: str
    indicators: list[dict]   # [{id, name, value, date, unit, change_1m}]
    warnings: list[str]

    def to_dict(self) -> dict:
        return {
            "fetched_at": self.fetched_at,
            "indicators": self.indicators,
            "warnings": self.warnings,
        }

    def to_brief_text(self) -> str:
        """Compact text representation for Claude prompt injection."""
        lines = [f"Macro Snapshot ({self.fetched_at})", "-" * 40]
        for ind in self.indicators:
            change = f" | 1M chg: {ind['change_1m']:+.2f}" if ind.get("change_1m") is not None else ""
            lines.append(f"{ind['name']}: {ind['value']} {ind['unit']}{change}")
        return "\n".join(lines)


def fetch_series(series_id: str, api_key: str, lookback_days: int = 60) -> list[dict]:
    """Fetch FRED series observations for the past N days."""
    start = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start,
        "sort_order": "desc",
        "limit": 5,
    }
    resp = requests.get(FRED_BASE_URL, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json().get("observations", [])


def fetch_macro_snapshot(
    indicator_ids: Optional[list[str]] = None,
    api_key: Optional[str] = None,
) -> MacroSnapshot:
    """
    Fetch latest values for all configured macro indicators.

    Args:
        indicator_ids: List of FRED series IDs. If None, fetches all in INDICATOR_META.
        api_key: FRED API key. Falls back to FRED_API_KEY env var.

    Returns:
        MacroSnapshot with current values and 1-month changes.
    """
    api_key = api_key or os.getenv("FRED_API_KEY")
    if not api_key:
        raise ValueError("FRED_API_KEY not set. Get a free key at fred.stlouisfed.org")

    indicator_ids = indicator_ids or list(INDICATOR_META.keys())
    indicators = []
    warnings = []

    for series_id in indicator_ids:
        meta = INDICATOR_META.get(series_id, {"name": series_id, "unit": ""})
        try:
            obs = fetch_series(series_id, api_key)
            valid = [o for o in obs if o["value"] != "."]
            if not valid:
                warnings.append(f"No valid data for {series_id}")
                continue

            latest = float(valid[0]["value"])
            prev = float(valid[-1]["value"]) if len(valid) > 1 else None
            change = round(latest - prev, 4) if prev is not None else None

            indicators.append({
                "id": series_id,
                "name": meta["name"],
                "value": round(latest, 4),
                "date": valid[0]["date"],
                "unit": meta["unit"],
                "change_1m": change,
            })
        except Exception as e:
            warnings.append(f"Failed to fetch {series_id}: {e}")

    return MacroSnapshot(
        fetched_at=datetime.utcnow().isoformat(),
        indicators=indicators,
        warnings=warnings,
    )


if __name__ == "__main__":
    import json
    snapshot = fetch_macro_snapshot()
    print(json.dumps(snapshot.to_dict(), indent=2))
    print("\n--- Brief text for Claude ---")
    print(snapshot.to_brief_text())
