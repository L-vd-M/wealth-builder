# Feature To Page Mapping

## World Map Page
- Global region heat map (market movement)
- Macro events timeline
- Regional news highlights

## Quant Analysis Page
- Factor dashboard (momentum, volatility, carry)
- Screening and ranking tables
- Correlation and regime blocks
- Predefined quant strategies catalogue
- Agent-based trade verification panel
- Whale-copy verified strategy visibility
- Fixed-$5 trailing stop strategy visibility

## Financial Analysis Page
- Company/asset fundamentals
- Comparative valuation panels
- Earnings/event calendar

## Trading Page
- Watchlists
- Order ticket (paper mode first)
- Open positions and risk summary

## Platforms Directory Page
- Category tabs: Crypto / Forex / Stocks
- Platform cards: fees, markets, API quality, regions
- Comparison table and filters

## News Hub Page
- Streams: Financial, Crypto, World
- Sentiment tags and source filters
- Saved briefing snapshots

## Bots & Strategies Page
- Bot inventory and status
- Strategy library and performance summaries
- Deployment and monitoring placeholders
- Backtest execution against persisted historical data
- Strategy templates including whale-copy verification flow
- Trailing stop strategy simulation and rules

## AI Agents Console Page
- Chat with quant/trading assistants
- Strategy-to-spec generation
- Plot/overlay request panel
- Code/action proposal stream
- Research-agent verification support for trade approval workflows

## Strategy API Layer
- Predefined quant strategies endpoint (`/strategies/predefined`)
- Agent verification endpoint for trades (`/strategies/verify-trade`)
- Whale-copy plan endpoint with research gate (`/strategies/whale-copy/plan`)
- Fixed-dollar trailing stop endpoint (`/strategies/trailing-stop`)
- Historical OHLCV ingestion endpoint (`/strategies/historical/ingest`)
- Backtest runs persisted to database (`backtest_runs`)
- Historical market bars persisted for backtests (`historical_prices`)

## Strategy Documentation
- Implemented strategies reference (`docs/implemented-strategies.md`)
