# Implemented Strategies and Quant Endpoints

This document lists the quant strategies and strategy-related features currently implemented in Market Command.

## Important note on returns

No strategy guarantees strong or consistent returns. The strategies listed here are widely researched and historically effective in specific market regimes, but all remain sensitive to market conditions, execution quality, slippage, fees, and risk controls.

## Core strategy APIs

- GET /strategies/predefined
  - Returns all predefined strategy templates available for selection.
- POST /strategies/draft
  - Builds a strategy draft with signals and risk rules from a thesis.
- POST /strategies/verify-trade
  - Uses the research agent verification flow before approval.
- POST /strategies/whale-copy/plan
  - Generates a whale-copy plan and blocks execution if verification fails.
- POST /strategies/trailing-stop
  - Computes fixed-step trailing-stop levels (default step is 5.0).
- POST /strategies/backtest
  - Runs backtests using persisted OHLCV data from historical_prices.
- POST /strategies/historical/ingest
  - Ingests real exchange OHLCV candles into historical_prices before backtesting.

## Real-data ingestion support

Implemented exchanges for ingestion endpoint:

- binance
- kraken
- coinbase

Endpoint:

- POST /strategies/historical/ingest

Request fields:

- exchange: binance | kraken | coinbase
- symbol: trading pair, examples BTCUSDT, BTC/USD, BTC-USD
- timeframe: 1m | 5m | 15m | 30m | 1h | 4h | 1d
- limit: 50..1000
- since_ms: optional start timestamp in milliseconds
- replace_existing: whether to replace overlapping candles

## Predefined strategy list implemented so far

1. Momentum Breakout
2. Mean Reversion RSI
3. Whale Copy (Research Verified)
4. Fixed $5 Trailing Stop
5. Dual Moving Average Trend Following
6. Turtle Breakout (20/10)
7. Bollinger Mean Reversion
8. Donchian Channel Breakout
9. Opening Range Breakout (ORB)
10. Cross-Sectional Momentum Rotation
11. Pairs Trading (Z-Score)
12. Volatility Breakout (ATR Expansion)
13. MACD Trend Confirmation
14. Calendar Seasonality Rotation

## Already implemented persistence related to strategies

- historical_prices table
  - Stores OHLCV candles per symbol, timeframe, timestamp, and source.
- backtest_runs table
  - Stores strategy backtest metrics and metadata.

## Current behavior used by backtests

- Backtests prioritize real exchange-ingested candles (source not synthetic).
- If no real candles are present, synthetic data can still be generated as fallback.
- Backtest metadata records source labels used by each run.

## Related files

- apps/api/app/routes/strategies.py
- apps/api/app/models.py
- apps/web/app/quant-analysis/page.tsx
