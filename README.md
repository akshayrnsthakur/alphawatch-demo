# AlphaWatch 🔭
### Personal Portfolio Intelligence via Claude AI

> A production-grade decision-support system for a crypto-concentrated, macro-aware investor.  
> Built to demonstrate thoughtful AI integration — not AI hype.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Claude Sonnet](https://img.shields.io/badge/AI-Claude%20Sonnet-orange.svg)](https://anthropic.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## The Problem

Managing a complex personal portfolio — concentrated crypto exposure, illiquid private equity, real estate across geographies, active thematic bets — produces more noise than signal. Monthly portfolio reviews were unfocused. The macro environment wasn't being connected to specific positions. Risk was being felt, not measured.

Most "AI portfolio" tools either make autonomous decisions (unauditable, unreliable) or just chat about markets (no structure). Neither was useful.

## The Solution

AlphaWatch is a **decision-support system** with a clean architectural principle:

> **Python calculates. Claude interprets. Humans decide.**

Every number is deterministic and reproducible. Every Claude output is logged with full inputs for auditability. No autonomous actions. No black boxes.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    AlphaWatch System                    │
│                                                         │
│  ┌─────────────────────┐   ┌─────────────────────────┐  │
│  │  DETERMINISTIC      │   │    CLAUDE AI LAYER      │  │
│  │  ENGINE             │──▶│                         │  │
│  │                     │   │  • Weekly brief         │  │
│  │  • Concentration    │   │  • Macro synthesis      │  │
│  │    risk calc        │   │  • Thematic signals     │  │
│  │  • Stress testing   │   │  • Anomaly detection    │  │
│  │  • Hedge sizing     │   │  • Wealth tracking      │  │
│  │  • Price feeds      │   │                         │  │
│  └─────────────────────┘   └─────────────────────────┘  │
│             │                          │                 │
│             └────────────┬─────────────┘                 │
│                          ▼                               │
│                 ┌─────────────────┐                      │
│                 │  HUMAN REVIEW   │                      │
│                 │  (You decide)   │                      │
│                 └─────────────────┘                      │
└─────────────────────────────────────────────────────────┘
```

### Three Parallel Tracks

| Track | What it does |
|-------|-------------|
| **Defensive** | Concentration risk, stress testing, hedging policy |
| **Offensive** | Thematic thesis tracking, alt rotation signals, DeFi yield |
| **Monitoring** | Daily macro digest, portfolio news, anomaly detection |

---

## Why This Claude Integration Pattern Works

This is the part worth studying if you're evaluating LLM architecture decisions.

### What Claude does in AlphaWatch:
- **Heterogeneous synthesis** — connecting FRED macro data + crypto prices + news into coherent narrative
- **Portfolio-specific interpretation** — "what does this Fed announcement mean for *this* portfolio's specific exposures"
- **Anomaly recognition** — pattern-matching across data in ways deterministic rules miss
- **Structured communication** — turning JSON reports into readable, actionable weekly briefs

### What Claude explicitly does NOT do:
- ❌ Determine portfolio allocations
- ❌ Generate trading signals  
- ❌ Calculate risk metrics
- ❌ Execute or recommend specific trades

### Key design decisions:
1. **Versioned prompt templates** stored in `ai/prompts/` — prompts are first-class artifacts, not inline strings
2. **Full audit logging** — every Claude call logged with complete inputs + outputs to `outputs/logs/audit.jsonl`
3. **Rich context injection** — portfolio owner background, active theses, constraints baked into system prompt
4. **Graceful degradation** — news fetch failure doesn't break the weekly brief; each data source fails independently
5. **Structured output enforcement** — output format specified in system prompt, not post-processed

---

## Portfolio Context

This system is built around a specific investor profile:

- **~65% crypto-correlated** exposure (crypto + crypto-infrastructure private equity)
- **~35% illiquid** (real estate + locked private equity) — can't rebalance quickly  
- **Active theses:** Crypto custody infrastructure, AI buildout, nuclear renaissance, India growth
- **10-year goal:** Accumulate sufficient capital to deploy as an angel/LP investor
- **Primary risk:** Crypto winter wiping liquid holdings before a private equity liquidity event

The defensive layer is specifically sized around this risk — not generic 60/40 portfolio management.

---

## Repo Structure

```
alphawatch/
├── config/
│   └── portfolio.yaml          # Your thesis in code — edit to update strategy
├── core/
│   ├── risk/
│   │   ├── concentration.py    # Correlation-adjusted exposure + alerts
│   │   ├── stress_test.py      # Scenario modeling (crypto winter, black swan, etc.)
│   │   └── hedging.py          # BTC options hedge sizing
│   ├── offense/
│   │   ├── thematic.py         # AI/nuclear/crypto thesis signal tracking
│   │   ├── alt_rotation.py     # Alt rebalancing signals
│   │   └── yield_optimizer.py  # Stablecoin + DeFi yield tracking
│   └── monitoring/
│       ├── macro.py            # FRED data feeds
│       ├── news.py             # Thematic news aggregation
│       └── portfolio_tracker.py # Live price feeds (CoinGecko + Yahoo Finance)
├── ai/
│   ├── analyst.py              # Claude API wrapper — the showcase component
│   └── prompts/                # Versioned prompt templates
│       ├── weekly_brief_system.txt
│       ├── anomaly_system.txt
│       └── macro_system.txt
├── outputs/
│   ├── reports/                # Generated weekly briefs (markdown)
│   └── logs/                   # Full audit trail (JSONL)
├── scheduler/
│   ├── daily.py                # Morning monitoring run
│   └── weekly.py               # Sunday report generation
└── tests/
```

---

## Quick Start

```bash
# Clone
git clone https://github.com/akshayrnsthakur/alphawatch-demo
cd alphawatch-demo

# Install dependencies
pip install -r requirements.txt

# Configure
cp config/portfolio.yaml config/my_portfolio.yaml
# Edit my_portfolio.yaml — add to .gitignore before committing

# Set API keys
cp .env.example .env
# Edit .env with your keys

# Run concentration analysis (no API keys needed)
python core/risk/concentration.py

# Run stress tests
python core/risk/stress_test.py

# Generate weekly brief (requires ANTHROPIC_API_KEY)
python scheduler/weekly.py
```

---

## API Keys Required

| Service | Purpose | Cost |
|---------|---------|------|
| [Anthropic](https://console.anthropic.com) | Claude AI synthesis | Pay per use |
| [FRED](https://fred.stlouisfed.org/docs/api/api_key.html) | Macro data | Free |
| [NewsAPI](https://newsapi.org) | News aggregation | Free tier (100 req/day) |
| CoinGecko | Crypto prices | Free tier |
| Yahoo Finance | Equity prices | Free (via yfinance) |

---

## Updating Your Thesis

The system is config-driven. No code changes required for:
- Rebalancing positions → edit `positions` in `portfolio.yaml`
- Adding a new thematic bet → add to `thematic_bets.themes`
- Adjusting risk thresholds → edit `thresholds`
- Changing signal keywords → edit `signal_keywords` per theme

---

## Sample Output

```markdown
# AlphaWatch Weekly Brief — 2026-03-01

## Portfolio Status: WATCH 🟡

## Executive Summary
Crypto-correlated exposure at 64% remains within threshold but elevated 
given current macro uncertainty. The Fed's hawkish pivot signals extend 
the high-rate environment, pressuring risk assets into Q2. BitGo equity 
thesis remains intact — institutional crypto AUM hitting new highs despite 
price volatility.

## Key Risks This Week
1. BTC consolidation below $80K signals potential retest of $72K support
2. Yield spread inversion deepening — historical precursor to risk-off
3. Illiquid RE position limits rebalancing optionality if correction accelerates

## Recommended Human Actions
- [ ] Review hedge coverage — BTC put options may be underweight given volatility
- [ ] Monitor: Fed minutes release Thursday
- [ ] No portfolio changes recommended — thesis intact, stay the course
```

---

## Limitations

- **Not financial advice.** Personal tool for a specific situation.
- **No backtesting.** Signals are not optimized on historical data — intentional to avoid p-hacking.
- **Manual RE valuation.** Real estate updated quarterly by hand.
- **No auto-trading.** All recommendations require human action.
- **Claude can be wrong.** All AI analysis is a starting point, not a conclusion.

---

## Tech Stack

- **Language:** Python 3.11+
- **AI:** Anthropic Claude Sonnet (`claude-sonnet-4-6`)
- **Data:** FRED API, CoinGecko, Yahoo Finance, NewsAPI
- **Scheduling:** AWS Lambda (production) / `schedule` library (local)
- **Config:** YAML
- **Storage:** Local filesystem + S3 (production)

---

## The Broader Point

AlphaWatch is as much an architectural demonstration as a financial tool. The pattern — deterministic calculation layer + LLM interpretation layer + human decision layer — applies broadly:

- Replace "portfolio" with "customer data" → customer intelligence system
- Replace "macro signals" with "competitive signals" → market intelligence system  
- Replace "stress tests" with "scenario modeling" → strategic planning system

The key insight is knowing what LLMs are actually good at (synthesis, interpretation, communication) vs. what they shouldn't do (calculation, execution, autonomous decisions).

---

*Built with Claude. Designed to showcase thoughtful AI integration.*  
*Questions or feedback: [github.com/akshayrnsthakur](https://github.com/akshayrnsthakur)*
