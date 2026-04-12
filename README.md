# Wealth Builder

Bloomberg-terminal-inspired trading platform with a Next.js frontend, a FastAPI backend, PostgreSQL persistence, Clerk authentication, cron scheduling, agent management, multi-agent trade deliberations, and linked trading wallets.

## Stack

- Frontend: Next.js, TypeScript, Tailwind CSS, Clerk
- Backend: FastAPI, SQLAlchemy async, PostgreSQL, APScheduler
- Workspace: monorepo with `apps/web` and `apps/api`
- Deployment: Vercel frontend plus Raspberry Pi backend over Cloudflare Tunnel

## Main features

- Trading and quant analysis pages
- Strategy drafting, saving, history, and bot creation
- Agent catalogue seeded from `project-agent-templates`
- Multi-agent trade deliberation records
- Wallet linking with encrypted API credential storage
- Scheduled cron jobs from inside the application

## Run locally

1. Install Node dependencies:

```bash
npm install
cd apps/web && npm install && cd ../..
```

2. Set up the API virtual environment:

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ../..
```

3. Create env files from the examples:

- `.env.example` -> `.env`
- `apps/api/.env.example` -> `apps/api/.env`

4. Start the dev stack:

```bash
npm run dev
```

## API route groups

- `/market/*`
- `/news/*`
- `/trading/*`
- `/strategies/*`
- `/agents/*`
- `/overlays/*`
- `/cron/*`
- `/registry/*`
- `/deliberations/*`
- `/wallets/*`

## Deployment docs

- `docs/raspberry-pi-setup.md`
- `DEPLOYMENT.md`
- `NEXT_STEPS.md`
- `deploy/ansible/README.md`

## Planning docs

- `docs/project-plan.md`
- `docs/feature-map.md`
- `docs/goals-and-milestones.md`
