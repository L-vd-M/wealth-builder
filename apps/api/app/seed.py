"""Seed system agent definitions into the database on first startup.

Agents are loaded from the project-agent-templates repository structure.
If the templates directory is absent the seed is silently skipped — agents
can still be added manually through the registry API.
"""
import logging
import os
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentDefinition

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Built-in agent catalogue (metadata only – full prompts loaded from disk)
# ---------------------------------------------------------------------------

_AGENTS: list[dict] = [
    # Alpaca
    {"slug": "alpaca-analysis", "name": "Alpaca Analysis Agent", "platform": "alpaca", "role": "analysis",
     "description": "Analyses Alpaca market data and charts for US stocks and crypto. Interprets RSI, MACD, Bollinger Bands, volume patterns, support/resistance levels, and trend signals.",
     "tools": ["read", "search", "run_in_terminal", "create_file"]},
    {"slug": "alpaca-chart", "name": "Alpaca Chart Agent", "platform": "alpaca", "role": "chart",
     "description": "Generates professional candlestick charts with technical indicators for US stocks and crypto using Alpaca market data.",
     "tools": ["read", "edit", "run_in_terminal", "create_file", "search"]},
    {"slug": "alpaca-decision", "name": "Alpaca Decision Agent", "platform": "alpaca", "role": "decision",
     "description": "Evaluates technical analysis reports and research to make BUY/SELL/HOLD trade decisions for Alpaca markets. Outputs a structured trade proposal with entry price, stop-loss, take-profit, position size, and confidence score.",
     "tools": ["read", "search", "create_file"]},
    {"slug": "alpaca-execution", "name": "Alpaca Execution Agent", "platform": "alpaca", "role": "execution",
     "description": "Places trades on Alpaca (stocks and crypto) based on confirmed signals from the Alpaca Decision Agent. Requires explicit user confirmation before executing live trades.",
     "tools": ["read", "run_in_terminal", "create_file"]},
    # Binance
    {"slug": "binance-analysis", "name": "Binance Analysis Agent", "platform": "binance", "role": "analysis",
     "description": "Analyses Binance kline (OHLCV) data and chart indicators for crypto spot and futures markets. Interprets RSI, MACD, Bollinger Bands, volume patterns, and funding rates.",
     "tools": ["read", "search", "run_in_terminal", "create_file"]},
    {"slug": "binance-chart", "name": "Binance Chart Agent", "platform": "binance", "role": "chart",
     "description": "Generates professional candlestick charts with technical indicators for Binance spot and futures markets.",
     "tools": ["read", "edit", "run_in_terminal", "create_file", "search"]},
    {"slug": "binance-decision", "name": "Binance Decision Agent", "platform": "binance", "role": "decision",
     "description": "Evaluates technical analysis reports to make BUY/SELL/HOLD crypto trade decisions for Binance spot and futures markets. Outputs structured trade proposals with entry, stop-loss, take-profit, position size, and leverage guidance.",
     "tools": ["read", "search", "create_file"]},
    {"slug": "binance-execution", "name": "Binance Execution Agent", "platform": "binance", "role": "execution",
     "description": "Places trades on Binance spot and futures markets. Supports market, limit, stop-limit, and OCO orders. Requires explicit user confirmation before executing live trades.",
     "tools": ["read", "run_in_terminal", "create_file"]},
    # Coinbase
    {"slug": "coinbase-analysis", "name": "Coinbase Analysis Agent", "platform": "coinbase", "role": "analysis",
     "description": "Analyses Coinbase Advanced Trade market data and charts for crypto markets. Interprets RSI, MACD, Bollinger Bands, volume, and price patterns.",
     "tools": ["read", "search", "run_in_terminal", "create_file"]},
    {"slug": "coinbase-chart", "name": "Coinbase Chart Agent", "platform": "coinbase", "role": "chart",
     "description": "Generates candlestick charts with technical indicators for Coinbase Advanced Trade crypto markets.",
     "tools": ["read", "edit", "run_in_terminal", "create_file", "search"]},
    {"slug": "coinbase-decision", "name": "Coinbase Decision Agent", "platform": "coinbase", "role": "decision",
     "description": "Evaluates technical analysis reports to make BUY/SELL/HOLD crypto trade decisions for Coinbase Advanced Trade markets.",
     "tools": ["read", "search", "create_file"]},
    {"slug": "coinbase-execution", "name": "Coinbase Execution Agent", "platform": "coinbase", "role": "execution",
     "description": "Places trades on Coinbase Advanced Trade. Defaults to limit orders to minimise fees. Requires explicit user confirmation before executing live trades.",
     "tools": ["read", "run_in_terminal", "create_file"]},
    # Interactive Brokers
    {"slug": "ibkr-analysis", "name": "Interactive Brokers Analysis Agent", "platform": "ibkr", "role": "analysis",
     "description": "Analyses IBKR market data across stocks, futures, forex, and options. Interprets RSI, MACD, Bollinger Bands, implied volatility, and price patterns.",
     "tools": ["read", "search", "run_in_terminal", "create_file"]},
    {"slug": "ibkr-chart", "name": "Interactive Brokers Chart Agent", "platform": "ibkr", "role": "chart",
     "description": "Generates candlestick charts with technical indicators for IBKR markets covering stocks, options, futures, forex, and crypto via ib_insync.",
     "tools": ["read", "edit", "run_in_terminal", "create_file", "search"]},
    {"slug": "ibkr-decision", "name": "Interactive Brokers Decision Agent", "platform": "ibkr", "role": "decision",
     "description": "Evaluates technical analysis reports to make BUY/SELL/HOLD trade decisions for IBKR markets spanning stocks, futures, forex, options, and crypto.",
     "tools": ["read", "search", "create_file"]},
    {"slug": "ibkr-execution", "name": "Interactive Brokers Execution Agent", "platform": "ibkr", "role": "execution",
     "description": "Places trades on Interactive Brokers via TWS API (ib_insync). Supports stocks, futures, forex, options, and crypto. Requires explicit user confirmation before live execution.",
     "tools": ["read", "run_in_terminal", "create_file"]},
    # Kraken
    {"slug": "kraken-analysis", "name": "Kraken Analysis Agent", "platform": "kraken", "role": "analysis",
     "description": "Analyses Kraken spot and futures crypto market data. Interprets OHLCV, VWAP, RSI, MACD, Bollinger Bands, and volume patterns.",
     "tools": ["read", "search", "run_in_terminal", "create_file"]},
    {"slug": "kraken-chart", "name": "Kraken Chart Agent", "platform": "kraken", "role": "chart",
     "description": "Generates candlestick charts with technical indicators for Kraken spot and futures crypto markets.",
     "tools": ["read", "edit", "run_in_terminal", "create_file", "search"]},
    {"slug": "kraken-decision", "name": "Kraken Decision Agent", "platform": "kraken", "role": "decision",
     "description": "Evaluates technical analysis reports to make BUY/SELL/HOLD crypto trade decisions for Kraken spot and futures markets.",
     "tools": ["read", "search", "create_file"]},
    {"slug": "kraken-execution", "name": "Kraken Execution Agent", "platform": "kraken", "role": "execution",
     "description": "Places trades on Kraken spot and futures markets. Supports market, limit, stop-loss, and take-profit orders. Requires explicit user confirmation before executing live trades.",
     "tools": ["read", "run_in_terminal", "create_file"]},
    # Luno
    {"slug": "luno-analysis", "name": "Luno Analysis Agent", "platform": "luno", "role": "analysis",
     "description": "Analyses Luno ZAR crypto market data. Interprets OHLCV, RSI, MACD, Bollinger Bands for ZAR-denominated pairs. Accounts for ZAR volatility and South African market hours.",
     "tools": ["read", "search", "run_in_terminal", "create_file"]},
    {"slug": "luno-chart", "name": "Luno Chart Agent", "platform": "luno", "role": "chart",
     "description": "Generates candlestick charts with technical indicators for Luno ZAR crypto markets. Handles pairs like XBTZAR and ETHZAR.",
     "tools": ["read", "edit", "run_in_terminal", "create_file", "search"]},
    {"slug": "luno-decision", "name": "Luno Decision Agent", "platform": "luno", "role": "decision",
     "description": "Evaluates technical analysis reports to make BUY/SELL/HOLD crypto trade decisions for Luno ZAR markets. Favours limit orders to exploit Luno's 0% maker fee.",
     "tools": ["read", "search", "create_file"]},
    {"slug": "luno-execution", "name": "Luno Execution Agent", "platform": "luno", "role": "execution",
     "description": "Places trades on Luno ZAR spot markets. Defaults to limit orders to exploit 0% maker fee. Requires explicit user confirmation before executing live trades.",
     "tools": ["read", "run_in_terminal", "create_file"]},
    # OANDA
    {"slug": "oanda-analysis", "name": "OANDA Analysis Agent", "platform": "oanda", "role": "analysis",
     "description": "Analyses OANDA forex and CFD market data across 70+ currency pairs, commodities, and indices. Interprets RSI, MACD, Bollinger Bands, ATR, and economic calendar context.",
     "tools": ["read", "search", "run_in_terminal", "create_file"]},
    {"slug": "oanda-chart", "name": "OANDA Chart Agent", "platform": "oanda", "role": "chart",
     "description": "Generates candlestick charts with technical indicators for OANDA forex and CFD markets using oandapyV20. Supports 70+ currency pairs with data back to 2005.",
     "tools": ["read", "edit", "run_in_terminal", "create_file", "search"]},
    {"slug": "oanda-decision", "name": "OANDA Decision Agent", "platform": "oanda", "role": "decision",
     "description": "Evaluates technical analysis reports to make BUY/SELL/HOLD forex and CFD trade decisions on OANDA. Outputs structured trade proposals with pip values and position sizing.",
     "tools": ["read", "search", "create_file"]},
    {"slug": "oanda-execution", "name": "OANDA Execution Agent", "platform": "oanda", "role": "execution",
     "description": "Places trades on OANDA forex and CFD markets via the v20 REST API. Practice environment available by default. Requires explicit user confirmation before live execution.",
     "tools": ["read", "run_in_terminal", "create_file"]},
    # VALR
    {"slug": "valr-analysis", "name": "VALR Analysis Agent", "platform": "valr", "role": "analysis",
     "description": "Analyses VALR ZAR and USDT crypto market data. Interprets OHLCV candles, RSI, MACD, Bollinger Bands, funding rates, and open interest for spot and futures.",
     "tools": ["read", "search", "run_in_terminal", "create_file"]},
    {"slug": "valr-chart", "name": "VALR Chart Agent", "platform": "valr", "role": "chart",
     "description": "Generates candlestick charts with technical indicators for VALR ZAR and stable-coin crypto markets. Supports spot and VALR Futures pairs.",
     "tools": ["read", "edit", "run_in_terminal", "create_file", "search"]},
    {"slug": "valr-decision", "name": "VALR Decision Agent", "platform": "valr", "role": "decision",
     "description": "Evaluates technical analysis reports to make BUY/SELL/HOLD crypto trade decisions for VALR spot and perpetual futures. Accounts for VALR fee tiers and futures funding rates.",
     "tools": ["read", "search", "create_file"]},
    {"slug": "valr-execution", "name": "VALR Execution Agent", "platform": "valr", "role": "execution",
     "description": "Places spot and perpetual futures trades on VALR. Supports limit, market, stop-limit, and batch orders. Uses HMAC-SHA512 authentication. Requires explicit user confirmation.",
     "tools": ["read", "run_in_terminal", "create_file"]},
    # Market-data agents
    {"slug": "coingecko-analysis", "name": "CoinGecko Analysis Agent", "platform": "market-data", "role": "data",
     "description": "Researches crypto market opportunities, identifies trending coins, compares market caps, and analyses DEX/on-chain token data. Uses the CoinGecko API (free Demo key).",
     "tools": ["read", "search", "run_in_terminal", "create_file", "web"]},
    {"slug": "macro-context", "name": "Macro Context Agent", "platform": "market-data", "role": "data",
     "description": "Assesses the macroeconomic backdrop for crypto, stocks, and forex trades. Fetches interest rates, inflation, GDP, employment, treasury yields, and DXY from FRED.",
     "tools": ["read", "search", "run_in_terminal", "create_file", "web"]},
    {"slug": "multi-asset-research", "name": "Multi-Asset Research Agent", "platform": "market-data", "role": "data",
     "description": "Researches across multiple asset classes simultaneously. Uses OpenBB and Twelve Data. Produces a cross-asset opportunity report.",
     "tools": ["read", "search", "run_in_terminal", "create_file", "web"]},
    {"slug": "on-chain-analysis", "name": "On-Chain Analysis Agent", "platform": "market-data", "role": "data",
     "description": "Analyses Bitcoin/Ethereum on-chain health metrics, exchange flows, MVRV/SOPR/NUPL cycle position. Uses Glassnode and Santiment APIs.",
     "tools": ["read", "search", "run_in_terminal", "create_file", "web"]},
    {"slug": "social-sentiment", "name": "Social Sentiment Agent", "platform": "market-data", "role": "sentiment",
     "description": "Assesses crypto market sentiment from social media. Uses LunarCrush Galaxy Score, AltRank, and Santiment social metrics to identify momentum coins.",
     "tools": ["read", "search", "run_in_terminal", "create_file", "web"]},
    {"slug": "stock-screener", "name": "Stock Screener Agent", "platform": "market-data", "role": "data",
     "description": "Screens US equities by fundamental or technical criteria. Uses yfinance, FinancialModelingPrep, and Finviz screener. Produces a ranked stock watchlist.",
     "tools": ["read", "search", "run_in_terminal", "create_file", "web"]},
    {"slug": "tradingview-signal", "name": "TradingView Signal Agent", "platform": "market-data", "role": "data",
     "description": "Processes TradingView Pine Script webhook alerts and routes them to downstream analysis or execution agents.",
     "tools": ["read", "edit", "run_in_terminal", "create_file", "search"]},
    # General financial agents
    {"slug": "financial-analyst", "name": "Financial Analyst Agent", "platform": "general", "role": "analyst",
     "description": "Analyses financial performance, compares scenarios, builds forecasts, identifies cost/revenue trends, and evaluates business cases with data.",
     "tools": ["read", "search", "run_in_terminal", "create_file", "web"]},
    {"slug": "trader", "name": "Trader Agent", "platform": "general", "role": "orchestrator",
     "description": "Structures trading plans with explicit risk controls and scenario-based thinking. Defines entry, sizing, stop-loss, and take-profit plans.",
     "tools": ["read", "search", "web", "todo"]},
    {"slug": "chartered-accountant", "name": "Chartered Accountant Agent", "platform": "general", "role": "analyst",
     "description": "Evaluates accounting treatment, validates compliance-oriented bookkeeping decisions, and prepares accounting control recommendations.",
     "tools": ["read", "search", "run_in_terminal", "create_file"]},
]


def _load_system_prompt(slug: str) -> str | None:
    """Try to load the full system prompt from the templates directory."""
    # Map slug -> relative file path in the templates repo
    _slug_to_file = {
        "alpaca-analysis": "agents/financial/alpaca/alpaca-analysis.agent.md",
        "alpaca-chart": "agents/financial/alpaca/alpaca-chart.agent.md",
        "alpaca-decision": "agents/financial/alpaca/alpaca-decision.agent.md",
        "alpaca-execution": "agents/financial/alpaca/alpaca-execution.agent.md",
        "binance-analysis": "agents/financial/binance/binance-analysis.agent.md",
        "binance-chart": "agents/financial/binance/binance-chart.agent.md",
        "binance-decision": "agents/financial/binance/binance-decision.agent.md",
        "binance-execution": "agents/financial/binance/binance-execution.agent.md",
        "coinbase-analysis": "agents/financial/coinbase/coinbase-analysis.agent.md",
        "coinbase-chart": "agents/financial/coinbase/coinbase-chart.agent.md",
        "coinbase-decision": "agents/financial/coinbase/coinbase-decision.agent.md",
        "coinbase-execution": "agents/financial/coinbase/coinbase-execution.agent.md",
        "ibkr-analysis": "agents/financial/interactive-brokers/ibkr-analysis.agent.md",
        "ibkr-chart": "agents/financial/interactive-brokers/ibkr-chart.agent.md",
        "ibkr-decision": "agents/financial/interactive-brokers/ibkr-decision.agent.md",
        "ibkr-execution": "agents/financial/interactive-brokers/ibkr-execution.agent.md",
        "kraken-analysis": "agents/financial/kraken/kraken-analysis.agent.md",
        "kraken-chart": "agents/financial/kraken/kraken-chart.agent.md",
        "kraken-decision": "agents/financial/kraken/kraken-decision.agent.md",
        "kraken-execution": "agents/financial/kraken/kraken-execution.agent.md",
        "luno-analysis": "agents/financial/luno/luno-analysis.agent.md",
        "luno-chart": "agents/financial/luno/luno-chart.agent.md",
        "luno-decision": "agents/financial/luno/luno-decision.agent.md",
        "luno-execution": "agents/financial/luno/luno-execution.agent.md",
        "oanda-analysis": "agents/financial/oanda/oanda-analysis.agent.md",
        "oanda-chart": "agents/financial/oanda/oanda-chart.agent.md",
        "oanda-decision": "agents/financial/oanda/oanda-decision.agent.md",
        "oanda-execution": "agents/financial/oanda/oanda-execution.agent.md",
        "valr-analysis": "agents/financial/valr/valr-analysis.agent.md",
        "valr-chart": "agents/financial/valr/valr-chart.agent.md",
        "valr-decision": "agents/financial/valr/valr-decision.agent.md",
        "valr-execution": "agents/financial/valr/valr-execution.agent.md",
        "coingecko-analysis": "agents/financial/market-data/coingecko.agent.md",
        "macro-context": "agents/financial/market-data/macro-context.agent.md",
        "multi-asset-research": "agents/financial/market-data/multi-asset.agent.md",
        "on-chain-analysis": "agents/financial/market-data/on-chain.agent.md",
        "social-sentiment": "agents/financial/market-data/social-sentiment.agent.md",
        "stock-screener": "agents/financial/market-data/stock-screener.agent.md",
        "tradingview-signal": "agents/financial/market-data/tradingview-signal.agent.md",
        "financial-analyst": "agents/financial/financial-analyst.agent.md",
        "trader": "agents/financial/trader.agent.md",
        "chartered-accountant": "agents/financial/chartered-accountant.agent.md",
    }

    templates_root = Path(os.getenv("AGENT_TEMPLATES_PATH", "/tmp/project-agent-templates"))
    relative = _slug_to_file.get(slug)
    if not relative:
        return None
    path = templates_root / relative
    if not path.exists():
        return None

    content = path.read_text(encoding="utf-8")
    # Strip YAML frontmatter (--- ... ---) to get just the system prompt body
    stripped = re.sub(r"^---\n.*?\n---\n", "", content, count=1, flags=re.DOTALL)
    return stripped.strip() or None


async def seed_system_agents(session: AsyncSession) -> None:
    """Insert built-in system agents if they don't already exist."""
    existing = set(
        (await session.execute(select(AgentDefinition.slug).where(AgentDefinition.is_system == True)))
        .scalars()
        .all()
    )
    if existing:
        return  # Already seeded

    log.info("Seeding %d system agent definitions…", len(_AGENTS))
    for meta in _AGENTS:
        agent = AgentDefinition(
            slug=meta["slug"],
            name=meta["name"],
            description=meta.get("description"),
            platform=meta.get("platform"),
            role=meta.get("role"),
            system_prompt=_load_system_prompt(meta["slug"]),
            tools_json=meta.get("tools"),
            is_system=True,
            user_id=None,
        )
        session.add(agent)

    await session.commit()
    log.info("System agents seeded successfully")
