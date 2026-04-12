# MarketCommand

Bloomberg-terminal-inspired multi-page trading and quant platform.

## Stack
- Frontend: Next.js + TypeScript + Tailwind
- Backend: FastAPI (Python)
- Workspace: Monorepo (`apps/web`, `apps/api`)

## Run Locally
1. Install Node deps:
   - `npm install`
   - `cd apps/web && npm install && cd ../..`
2. Set Python env for API:
   - `cd apps/api`
   - `python -m venv .venv && source .venv/bin/activate`
   - `pip install -r requirements.txt`
3. Start both services from repo root:
   - `npm run dev`

## Initial Pages
- World Map
- Quant Analysis
- Financial Analysis
- Trading Workspace
- Platforms Directory (Crypto / Forex / Stocks)
- News Hub (Financial / Crypto / World)
- Bots & Strategies
- AI Strategy Agent Console

## API Route Groups
- `/market/*`
- `/news/*`
- `/trading/*`
- `/strategies/*`
- `/agents/*`
- `/overlays/*`

## Planning Docs
- `docs/project-plan.md`
- `docs/feature-map.md`
- `docs/goals-and-milestones.md`
