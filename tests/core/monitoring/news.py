"""
core/monitoring/news.py
=======================
News aggregation for portfolio-relevant signals.

Sources (configure which to enable):
- NewsAPI (free tier — 100 req/day)
- RSS feeds (no API key needed)
- CryptoPanic (crypto-specific)

Fetches headlines filtered by thematic keywords from portfolio.yaml.
Returns structured headlines for Claude synthesis — no interpretation here.
"""

from __future__ import annotations
import os
import requests
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional
from ..risk.concentration import load_config


NEWSAPI_URL = "https://newsapi.org/v2/everything"


@dataclass
class NewsSnapshot:
    fetched_at: str
    articles: list[dict]     # [{title, source, url, published_at, matched_theme}]
    query_terms: list[str]

    def to_dict(self) -> dict:
        return {
            "fetched_at": self.fetched_at,
            "article_count": len(self.articles),
            "articles": self.articles,
        }

    def to_brief_text(self) -> str:
        """Compact text for Claude prompt injection."""
        lines = [f"News Headlines ({self.fetched_at})", "-" * 40]
        for a in self.articles[:15]:  # Cap at 15 for prompt size
            lines.append(f"[{a.get('matched_theme', 'general')}] {a['title']} — {a['source']}")
        return "\n".join(lines)


def build_query_from_themes(config: dict) -> tuple[str, dict[str, list[str]]]:
    """Extract keywords from thematic_bets and build NewsAPI query."""
    themes = config.get("thematic_bets", {}).get("themes", {})
    all_keywords = []
    keyword_to_theme = {}

    for theme_id, theme in themes.items():
        kws = theme.get("signal_keywords", [])
        for kw in kws:
            all_keywords.append(kw)
            keyword_to_theme.setdefault(kw.lower(), theme_id)

    query = " OR ".join(f'"{kw}"' for kw in all_keywords[:10])  # NewsAPI limit
    return query, keyword_to_theme


def fetch_news(
    api_key: Optional[str] = None,
    lookback_days: int = 2,
    config: Optional[dict] = None,
) -> NewsSnapshot:
    """
    Fetch relevant news articles based on portfolio thematic keywords.

    Args:
        api_key: NewsAPI key. Falls back to NEWS_API_KEY env var.
        lookback_days: How many days back to search.
        config: Portfolio config.

    Returns:
        NewsSnapshot with filtered, theme-tagged articles.
    """
    if config is None:
        config = load_config()

    api_key = api_key or os.getenv("NEWS_API_KEY")
    if not api_key:
        # Return empty snapshot — news is nice-to-have, not critical
        return NewsSnapshot(
            fetched_at=datetime.utcnow().isoformat(),
            articles=[],
            query_terms=[],
        )

    query, keyword_to_theme = build_query_from_themes(config)
    from_date = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    params = {
        "q": query,
        "from": from_date,
        "sortBy": "relevancy",
        "language": "en",
        "pageSize": 30,
        "apiKey": api_key,
    }

    articles = []
    try:
        resp = requests.get(NEWSAPI_URL, params=params, timeout=10)
        resp.raise_for_status()
        raw = resp.json().get("articles", [])

        for art in raw:
            title_lower = art.get("title", "").lower()
            matched_theme = next(
                (theme for kw, theme in keyword_to_theme.items() if kw in title_lower),
                "general"
            )
            articles.append({
                "title": art.get("title", ""),
                "source": art.get("source", {}).get("name", ""),
                "url": art.get("url", ""),
                "published_at": art.get("publishedAt", ""),
                "matched_theme": matched_theme,
            })
    except Exception as e:
        pass  # Fail silently — news is non-critical

    return NewsSnapshot(
        fetched_at=datetime.utcnow().isoformat(),
        articles=articles,
        query_terms=list(keyword_to_theme.keys()),
    )
