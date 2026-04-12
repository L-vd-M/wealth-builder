# Project Plan: MarketCommand

## Product Vision
Build a Bloomberg Terminal-style decision platform for multi-asset traders and analysts, combining world context, market analysis, execution workflows, strategy design, and AI-assisted quant development.

## Phase Roadmap

## Phase 0: Foundation (Week 1)
- Monorepo scaffold, CI baseline, environment setup
- Core navigation + route shells for every major module
- FastAPI route groups and mock data contracts

## Phase 1: MVP Insights (Weeks 2-4)
- World map page with market heat overlays
- Quant + financial analysis dashboards (core charts + metrics)
- News hub with categorized streams (financial, crypto, world)
- Platforms directory with filters: crypto, forex, stocks

## Phase 2: Trading Workbench (Weeks 5-7)
- Trading page with watchlists, paper execution panel, order tickets
- Trading bots page with status, logs, and controls
- Trading strategies page with templates and backtest summaries

## Phase 3: AI Analyst Console (Weeks 8-10)
- AI chat page for quant/trading ideation
- Prompt-to-strategy scaffolding
- Plotting and overlay assistant endpoints (TradingView-style annotation schema)

## Phase 4: Production Hardening (Weeks 11-12)
- Auth, role permissions, audit logs
- Provider integrations (market/news brokers)
- Performance, observability, risk controls

## Architecture Goals
- Frontend-first UX with terminal-grade density
- Backend API contracts for modular data providers
- Clear separation: data ingestion, analytics, execution, AI tooling
- Extensible overlay/indicator engine

## Success Metrics
- Users can navigate all modules with consistent terminal UX
- Users can compare platforms by asset class in under 30s
- Users can run AI-assisted strategy ideation and produce a structured strategy spec
- Charts support at least 3 overlay types (trendline, moving average, volume profile placeholder)
