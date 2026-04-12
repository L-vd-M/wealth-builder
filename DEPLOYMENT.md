# MarketCommand — Deployment Guide

## Architecture

```
Browser
  │
  ▼ HTTPS
Vercel  ──────────────────────  Next.js frontend (free tier)
  │
  │ HTTPS  (NEXT_PUBLIC_API_URL)
  ▼
Cloudflare Tunnel  ──────────  free, no port-forwarding needed
  │
  ▼ HTTP (localhost)
Raspberry Pi
  ├── nginx  (port 80) ──────── reverse proxy
  ├── FastAPI (port 8000) ───── Python backend
  └── PostgreSQL (port 5432) ── local-only DB

Auth:   Clerk   (free ≤ 10 k MAU)
Email:  Resend  (free ≤ 3 k emails/month)
```

**Convex position in this setup**
Convex is optional and not required for the lowest-cost architecture.
PostgreSQL on the Pi handles strategy versioning at near-zero monthly cost.
Use Convex later for real-time fanout (live P&L streams, collaborative sessions, low-latency event feeds).

### Optional Convex add-on (future)
1. Create a Convex project and run convex dev once from the frontend app.
2. Store high-frequency ephemeral state in Convex (live bot heartbeat, stream events).
3. Keep canonical strategy versions and permissions in PostgreSQL.
4. Synchronize with an outbox pattern from FastAPI to Convex for eventually consistent updates.

---

## Monthly cost estimate

| Service | Free tier | Notes |
|---|---|---|
| Vercel (Hobby) | $0 | Next.js, CDN, serverless functions |
| Clerk | $0 ≤ 10 k MAU | Auth, JWKS |
| Resend | $0 ≤ 3 k emails | Strategy save notifications |
| Cloudflare Tunnel | $0 | Secure RPi exposure |
| Raspberry Pi | ~$5/mo electricity | 4B or 5 recommended |
| **Total** | **~$5/mo** | |

---

## Prerequisites

- Raspberry Pi 4B or 5 (4 GB RAM minimum recommended) running Raspberry Pi OS 64-bit
- Domain name (can use a free subdomain from Cloudflare or similar)
- Accounts: Clerk, Resend, Cloudflare, Vercel

---

## 1. Raspberry Pi — one-time setup

```bash
# On the Pi
bash deploy/setup-pi.sh

# Clone the repo
git clone https://github.com/youruser/market-command ~/marketcommand
cd ~/marketcommand

# Copy and fill out the env file
cp .env.example .env
nano .env
```

---

## 2. Clerk setup

1. Create a free account at https://clerk.com
2. Create a new application
3. In **API Keys** copy:
   - `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` → Vercel env + local `.env`
   - `CLERK_SECRET_KEY` → Vercel env only (never expose in frontend)
4. Note the **JWKS URL** (shows on the API Keys page):
   ```
   https://<your-clerk-domain>.clerk.accounts.dev/.well-known/jwks.json
   ```
   Add it to `.env` as `CLERK_JWKS_URL` and to Vercel as well.
5. In **Paths** → configure your Vercel domain as allowed origin.

### Protect additional routes

Edit `apps/web/middleware.ts` and add paths to `createRouteMatcher`.

---

## 3. Resend setup

1. Create a free account at https://resend.com
2. Add and verify your sending domain (or use the sandbox for testing)
3. Create an API key and add it to `.env` as `RESEND_API_KEY`
4. Set `RESEND_FROM_EMAIL` to a verified sender address

Notifications fire automatically whenever a user saves a strategy (if `RESEND_API_KEY` is set).

---

## 4. Cloudflare Tunnel — expose the Pi backend

```bash
# On the Pi
# Install cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb

# Authenticate (opens a browser link)
cloudflared tunnel login

# Create a tunnel
cloudflared tunnel create marketcommand-api

# Get the token (paste into .env as CLOUDFLARE_TUNNEL_TOKEN)
cloudflared tunnel token marketcommand-api
```

In the Cloudflare dashboard (Zero Trust → Networks → Tunnels):
- Add a public hostname: `api.yourdomain.com` → `http://localhost:80`

The Docker Compose stack includes a `cloudflared` service that picks up the token automatically.

---

## 5. Vercel — frontend deployment

```bash
# From your development machine
npm i -g vercel
vercel --cwd apps/web
```

Set these environment variables in the Vercel project dashboard:

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://api.yourdomain.com` |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | from Clerk dashboard |
| `CLERK_SECRET_KEY` | from Clerk dashboard |

> **Note:** `CLERK_SECRET_KEY` is used server-side only. Never expose it to the browser.

---

## 6. Start the Raspberry Pi stack

```bash
cd ~/marketcommand

# First run (builds the API image, ~3 min on Pi 4)
docker compose up -d --build

# Check logs
docker compose logs -f

# Verify API is up
curl http://localhost/health
# → {"status":"ok"}

# Verify Cloudflare Tunnel is routing correctly
curl https://api.yourdomain.com/health
# → {"status":"ok"}
```

PostgreSQL tables are created automatically on first startup via SQLAlchemy `create_all`.

---

## 7. Local development

```bash
# Terminal 1 — frontend
cd apps/web
pnpm dev  # http://localhost:3000

# Terminal 2 — backend (requires local Postgres or Docker)
cd apps/api
uvicorn app.main:app --reload
```

Required local env (copy `.env.example` → `.env` and fill in Clerk + DB values):

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/marketcommand
CLERK_JWKS_URL=https://...
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
ALLOWED_ORIGINS=http://localhost:3000
```

Start local Postgres quickly:
```bash
docker run -d --name pg-dev \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=marketcommand \
  -p 5432:5432 \
  postgres:16-alpine
```

---

## 8. Updating in production

```bash
# On the Pi — pull latest and rebuild only the API image
git pull
docker compose up -d --build api
```

---

## Database migrations (Alembic)

Alembic is included for future schema changes.

```bash
# initialise once (already done)
alembic init alembic

# generate a migration after model changes
alembic revision --autogenerate -m "add column xyz"

# apply
alembic upgrade head
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| 401 on `/strategies/save` | User is not signed in; check `CLERK_JWKS_URL` |
| Tunnel not connecting | Verify `CLOUDFLARE_TUNNEL_TOKEN` in `.env` |
| `asyncpg` connection refused | Postgres container not healthy yet; wait 10s and retry |
| Chart not rendering | Ensure `lightweight-charts` is installed (`pnpm install` in `apps/web`) |
