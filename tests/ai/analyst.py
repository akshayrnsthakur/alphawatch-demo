"""
ai/analyst.py
=============
Claude AI integration layer — the "analyst in a box."

This is the showcase component. It demonstrates:
- Rich context injection (portfolio owner background, theses, constraints)
- Structured output enforcement via prompts
- Clean separation: Python calculates, Claude interprets
- Full audit logging of every API call (inputs + outputs)
- Graceful error handling and retry logic

Claude is in the ANALYST seat, not the driver's seat.
Every output is for human review — never auto-executed.
"""

from __future__ import annotations
import os
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import anthropic

logger = logging.getLogger(__name__)

# Audit log path
AUDIT_LOG_PATH = Path(__file__).parents[1] / "outputs" / "logs" / "audit.jsonl"
REPORTS_PATH = Path(__file__).parents[1] / "outputs" / "reports"


def _log_audit(task: str, prompt: str, response: str, model: str, duration_s: float) -> None:
    """Append every Claude call to the audit trail. Non-negotiable for auditability."""
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "task": task,
        "model": model,
        "duration_s": round(duration_s, 2),
        "prompt_chars": len(prompt),
        "response_chars": len(response),
        "prompt": prompt,          # Full input logged for reproducibility
        "response": response,      # Full output logged
    }
    with open(AUDIT_LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


class AlphaWatchAnalyst:
    """
    Claude-powered analyst for AlphaWatch.

    Usage:
        analyst = AlphaWatchAnalyst()
        brief = analyst.generate_weekly_brief(
            concentration_report=conc_report.to_dict(),
            stress_results=[r.to_dict() for r in stress_results],
            macro_snapshot=macro.to_dict(),
            news_snapshot=news.to_dict(),
        )
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 4096,
    ):
        self.client = anthropic.Anthropic(
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY")
        )
        self.model = model
        self.max_tokens = max_tokens
        self._load_prompts()

    def _load_prompts(self) -> None:
        """Load versioned prompt templates from disk."""
        prompts_dir = Path(__file__).parent / "prompts"
        self.prompts = {}
        for f in prompts_dir.glob("*.txt"):
            self.prompts[f.stem] = f.read_text()

    def _call(self, task: str, system: str, user: str) -> str:
        """
        Core Claude API call with audit logging and retry.

        Args:
            task: Human-readable task name for audit log.
            system: System prompt.
            user: User/data prompt.

        Returns:
            Claude's response as a string.
        """
        start = time.time()
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            text = response.content[0].text
        except anthropic.RateLimitError:
            logger.warning("Rate limit hit — waiting 30s before retry")
            time.sleep(30)
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            text = response.content[0].text
        except Exception as e:
            logger.error(f"Claude API call failed for task '{task}': {e}")
            raise

        duration = time.time() - start
        _log_audit(task=task, prompt=f"SYSTEM:\n{system}\n\nUSER:\n{user}",
                   response=text, model=self.model, duration_s=duration)
        return text

    def generate_weekly_brief(
        self,
        concentration_report: dict,
        stress_results: list[dict],
        macro_snapshot: dict,
        news_snapshot: dict,
        hedge_report: Optional[dict] = None,
        owner_context: Optional[str] = None,
    ) -> str:
        """
        Generate the weekly portfolio intelligence brief.

        This is the primary output of AlphaWatch — a structured markdown report
        synthesizing all data sources into actionable analysis.

        Args:
            concentration_report: Output from concentration.run_concentration_analysis()
            stress_results: List of stress test results
            macro_snapshot: Output from macro.fetch_macro_snapshot()
            news_snapshot: Output from news.fetch_news()
            hedge_report: Optional hedge sizing output
            owner_context: Optional override for portfolio owner context

        Returns:
            Markdown-formatted weekly brief string.
        """
        system_prompt = self.prompts.get("weekly_brief_system", self._default_system_prompt())
        user_prompt = self._build_weekly_brief_prompt(
            concentration_report=concentration_report,
            stress_results=stress_results,
            macro_snapshot=macro_snapshot,
            news_snapshot=news_snapshot,
            hedge_report=hedge_report,
            owner_context=owner_context,
        )

        brief = self._call(
            task="weekly_brief",
            system=system_prompt,
            user=user_prompt,
        )

        # Save report to disk
        self._save_report(brief, report_type="weekly")
        return brief

    def analyze_anomaly(self, anomaly_data: dict) -> str:
        """
        Analyze a detected anomaly (price spike, news surge, threshold breach).

        Returns a concise analysis with possible explanations and watch items.
        """
        system_prompt = self.prompts.get("anomaly_system", self._default_system_prompt())
        user_prompt = f"""
ANOMALY DETECTED — Please analyze:

{json.dumps(anomaly_data, indent=2)}

Provide:
1. Most likely explanation (1-2 sentences)
2. Portfolio impact assessment (specific to positions above)
3. Watch items for next 24-48 hours
4. Action required? (yes/no — be conservative)
"""
        return self._call(task="anomaly_analysis", system=system_prompt, user=user_prompt)

    def synthesize_macro(self, macro_snapshot: dict, news_snapshot: dict) -> str:
        """
        Daily macro synthesis — shorter than weekly brief, focused on macro regime.
        """
        system_prompt = self.prompts.get("macro_system", self._default_system_prompt())
        user_prompt = f"""
Generate a concise daily macro synthesis for a crypto-concentrated portfolio investor.

MACRO DATA:
{json.dumps(macro_snapshot, indent=2)}

RECENT NEWS:
{json.dumps(news_snapshot.get('articles', [])[:10], indent=2)}

Format:
## Macro Regime (1 sentence)
## Key Signals (3 bullets max)
## Portfolio Implications (2-3 sentences specific to crypto/custody infra exposure)
## Watch This Week (2 bullets)
"""
        return self._call(task="macro_synthesis", system=system_prompt, user=user_prompt)

    def _build_weekly_brief_prompt(
        self,
        concentration_report: dict,
        stress_results: list[dict],
        macro_snapshot: dict,
        news_snapshot: dict,
        hedge_report: Optional[dict],
        owner_context: Optional[str],
    ) -> str:
        context = owner_context or self._default_owner_context()
        hedge_section = json.dumps(hedge_report, indent=2) if hedge_report else "Not provided."

        return f"""
{context}

---

Please generate the AlphaWatch Weekly Intelligence Brief using the data below.

## PORTFOLIO CONCENTRATION
{json.dumps(concentration_report, indent=2)}

## STRESS TEST RESULTS
{json.dumps(stress_results, indent=2)}

## MACRO SNAPSHOT
{json.dumps(macro_snapshot, indent=2)}

## NEWS SIGNALS
{json.dumps(news_snapshot.get('articles', [])[:20], indent=2)}

## HEDGE STATUS
{hedge_section}

---

Follow the brief format exactly as specified in your system prompt.
"""

    def _default_owner_context(self) -> str:
        return """
PORTFOLIO OWNER CONTEXT:
- Senior product leader at a crypto custody infrastructure company (BitGo)
- ~65% crypto-correlated portfolio exposure (crypto + crypto-infrastructure equity)
- ~40% illiquid (real estate in Hyderabad + locked private equity)
- Active theses: crypto custody infrastructure, AI buildout, nuclear renaissance, India growth
- Primary risk: crypto winter while illiquid assets prevent rebalancing
- Time horizon: 5-10 years for illiquid positions; tactical on liquid crypto
- This is NOT their primary income — they can ride out volatility
- They want honest analysis, not reassurance. Call out real risks.
"""

    def _default_system_prompt(self) -> str:
        return """
You are AlphaWatch, a personal portfolio intelligence analyst for a sophisticated investor.

YOUR ROLE:
- Synthesize data into clear, actionable analysis
- Be direct and honest — do not sugarcoat risks
- Connect macro signals to this specific portfolio's exposures
- Flag genuine concerns without crying wolf on every fluctuation
- Every recommendation requires human action — you do not execute anything

YOUR CONSTRAINTS:
- Do NOT generate specific allocation percentages or precise trade sizes
- Do NOT make confident return predictions
- Do NOT recommend specific securities not already in the portfolio
- DO flag when stress scenarios suggest liquidity risk
- DO highlight when thematic theses are being validated or challenged

OUTPUT FORMAT for Weekly Brief:
```
# AlphaWatch Weekly Brief — [Date]

## 🔴/🟡/🟢 Portfolio Status: [ONE WORD: ALERT / WATCH / STABLE]

## Executive Summary (3 sentences max)

## Macro Regime
[2-3 sentences on current macro environment relevant to this portfolio]

## Portfolio Health
### Concentration
### Liquidity
### Stress Test Highlights

## Thematic Thesis Tracker
[For each active thesis: status, latest signals, conviction change if any]

## Key Risks This Week
[Top 3, specific to this portfolio]

## Opportunities / Watch Items
[Top 2, specific to active theses]

## Recommended Human Actions
[Conservative list — only things with clear rationale. Default is "monitor"]
```

Remember: You are the analyst. The human is the decision-maker.
"""

    def _save_report(self, content: str, report_type: str) -> None:
        """Save generated report to outputs/reports/."""
        REPORTS_PATH.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = REPORTS_PATH / f"{report_type}_{timestamp}.md"
        filename.write_text(content)
        logger.info(f"Report saved: {filename}")


if __name__ == "__main__":
    # Demo run — uses placeholder data if no real data available
    analyst = AlphaWatchAnalyst()

    sample_concentration = {
        "total_portfolio_usd": 500000,
        "crypto_correlated_pct": 0.62,
        "illiquid_pct": 0.38,
        "alerts": [],
        "positions": [
            {"id": "BTC", "name": "Bitcoin", "pct_of_portfolio": 0.30, "liquidity": "liquid"},
            {"id": "ETH", "name": "Ethereum", "pct_of_portfolio": 0.20, "liquidity": "liquid"},
            {"id": "BITGO_EQUITY", "name": "BitGo Equity", "pct_of_portfolio": 0.12, "liquidity": "semi_liquid"},
            {"id": "RE_HYD", "name": "Hyderabad RE", "pct_of_portfolio": 0.38, "liquidity": "illiquid"},
        ],
    }

    sample_macro = {
        "fetched_at": datetime.utcnow().isoformat(),
        "indicators": [
            {"name": "Fed Funds Rate", "value": 4.33, "unit": "%", "change_1m": -0.25},
            {"name": "10Y-2Y Yield Spread", "value": 0.35, "unit": "%", "change_1m": 0.15},
            {"name": "VIX", "value": 18.5, "unit": "index", "change_1m": -2.1},
        ],
    }

    sample_stress = [
        {
            "scenario": "crypto_winter",
            "portfolio_loss_pct": -0.42,
            "liquid_remaining_usd": 87000,
            "alerts": [],
        }
    ]

    sample_news = {
        "articles": [
            {"title": "Fed signals pause in rate hikes", "source": "Reuters", "matched_theme": "general"},
            {"title": "Bitcoin ETF sees record inflows", "source": "Bloomberg", "matched_theme": "crypto_custody_infra"},
        ]
    }

    print("Generating weekly brief...")
    brief = analyst.generate_weekly_brief(
        concentration_report=sample_concentration,
        stress_results=sample_stress,
        macro_snapshot=sample_macro,
        news_snapshot=sample_news,
    )
    print(brief)
