# MarketCommand — Next Steps & Environment Variable Setup Guide

This guide tells you **exactly** where to sign up, what to copy, and which file to paste values into — for every external service the app depends on.

---

## Quick reference: which env vars go where

| Variable | Local `.env` | Vercel Dashboard | Pi `.env` |
|---|:---:|:---:|:---:|
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | ✅ | ✅ | — |
| `CLERK_SECRET_KEY` | ✅ | ✅ | — |
| `CLERK_JWKS_URL` | ✅ | ✅ | ✅ |
| `NEXT_PUBLIC_API_URL` | ✅ | ✅ | — |
| `DATABASE_URL` | ✅ | — | ✅ |
| `POSTGRES_USER` | — | — | ✅ |
| `POSTGRES_PASSWORD` | — | — | ✅ |
| `ALLOWED_ORIGINS` | ✅ | — | ✅ |
| `CLOUDFLARE_TUNNEL_TOKEN` | — | — | ✅ |
| `OPENAI_API_KEY` | ✅ | — | ✅ |
| `RESEND_API_KEY` | ✅ | — | ✅ |
| `RESEND_FROM_EMAIL` | ✅ | — | ✅ |

**Local `.env`** = `apps/web/.env.local` (frontend) + `apps/api/.env` (backend)  
**Vercel Dashboard** = project environment variables in your Vercel deployment  
**Pi `.env`** = `.env` file in `~/marketcommand/` on the Raspberry Pi

---

## Step 1 — Clerk (Authentication)

> **Free tier:** 10,000 Monthly Active Users  
> **Sign up:** https://clerk.com

### 1a. Create your application

1. Go to https://dashboard.clerk.com
2. Click **"Create application"**
3. Give it a name: `MarketCommand`
4. Choose sign-in methods: **Email** and/or **Google** (your preference)
5. Click **"Create application"**

### 1b. Get your API keys

On the **API Keys** page of your new application:

```
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxxxxxxxxx
CLERK_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxxxxx
```

- Copy the **Publishable key** — starts with `pk_test_` (development) or `pk_live_` (production)
- Copy the **Secret key** — starts with `sk_test_` or `sk_live_`

### 1c. Get your JWKS URL

Still on the **API Keys** page, scroll down to find:

```
https://<your-clerk-domain>.clerk.accounts.dev/.well-known/jwks.json
```

Example:  
```
https://glad-mink-42.clerk.accounts.dev/.well-known/jwks.json
```

This is your `CLERK_JWKS_URL`.

### 1d. Configure allowed origins

Go to **Configure → Restrictions → Allowed origins** and add:
- `http://localhost:3000` (local development)
- `https://your-app.vercel.app` (once deployed to Vercel)

### 1e. Where to add these values

**Frontend — `apps/web/.env.local`:**
```env
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxxxxxxxxx
CLERK_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxxxxx
```

**Backend — `apps/api/.env`:**
```env
CLERK_JWKS_URL=https://<your-clerk-domain>.clerk.accounts.dev/.well-known/jwks.json
```

**Vercel Dashboard** (Step 4 below):
```
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY   →  pk_live_...
CLERK_SECRET_KEY                    →  sk_live_...
CLERK_JWKS_URL                      →  https://...clerk.accounts.dev/.well-known/jwks.json
```

**Raspberry Pi — `~/marketcommand/.env`:**
```env
CLERK_JWKS_URL=https://<your-clerk-domain>.clerk.accounts.dev/.well-known/jwks.json
```

---

## Step 2 — Resend (Email notifications)

> **Free tier:** 3,000 emails/month, 1 domain  
> **Sign up:** https://resend.com/signup

### 2a. Create account and add your domain

1. Go to https://resend.com/domains
2. Click **"Add Domain"**
3. Enter your domain (e.g. `marketcommand.app`) — you need to own a domain for proper sending
4. Add the DNS records Resend shows you to your DNS provider (Cloudflare, Namecheap, etc.)
5. Click **"Verify DNS Records"** after adding them (takes 0–15 minutes)

> **Don't have a domain yet?** Use the Resend sandbox — you can receive on any email you verify without a domain. Go to **Audiences → Create audience**, then **Testing → Default domain** (something like `@resend.dev`).

### 2b. Create an API key

1. Go to https://resend.com/api-keys
2. Click **"Create API key"**
3. Name: `MarketCommand Production`
4. Permission: **Sending access**
5. Copy the key — shown once only

### 2c. Where to add these values

**Backend — `apps/api/.env`:**
```env
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx
RESEND_FROM_EMAIL=notifications@yourdomain.com
```

**Raspberry Pi — `~/marketcommand/.env`:**
```env
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx
RESEND_FROM_EMAIL=notifications@yourdomain.com
```

> If `RESEND_API_KEY` is left empty the app still works — email notifications are silently skipped.

---

## Step 3 — Cloudflare Tunnel (expose Raspberry Pi backend)

> **Free:** Always free for tunnels  
> **Requirements:** A domain added to your Cloudflare account  
> **Sign up:** https://dash.cloudflare.com/sign-up

### 3a. Add your domain to Cloudflare (if not already done)

1. Go to https://dash.cloudflare.com → **"Add a site"**
2. Enter your domain and choose the **Free plan**
3. Update your domain registrar's nameservers to point to Cloudflare's

### 3b. Create a Tunnel

1. Go to https://one.dash.cloudflare.com → **Networks → Tunnels**
2. Click **"Create a Tunnel"** → choose **"Cloudflared"**
3. Name: `marketcommand-api`
4. On the next screen, under **"Install and run a connector"**, copy the **Docker** command  
   The command contains your tunnel token like: `--token eyJhXXX...`
5. Copy just the token string (everything after `--token `)

### 3c. Configure the public hostname

Still in the Tunnel configuration → **Public Hostname** tab:
1. Click **"Add a public hostname"**
2. Fill in:
   - **Subdomain:** `api`
   - **Domain:** `yourdomain.com`
   - **Service → Type:** `HTTP`
   - **Service → URL:** `http://localhost:80`  ← nginx inside Docker
3. Click **Save hostname**

Your backend will be reachable at `https://api.yourdomain.com`

### 3d. Where to add these values

**Raspberry Pi — `~/marketcommand/.env`:**
```env
CLOUDFLARE_TUNNEL_TOKEN=eyJhXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

---

## Step 4 — Vercel (Frontend hosting)

> **Free tier:** Hobby plan — unlimited personal projects  
> **Sign up:** https://vercel.com/signup (use "Continue with GitHub")

### 4a. Import the repository

1. Go to https://vercel.com/new
2. Select your **L-vd-M/market-command** repository
3. Under **"Configure Project"**:
   - **Framework Preset:** Next.js (auto-detected)
   - **Root Directory:** `apps/web`
   - Leave other settings as default
4. Click **"Deploy"** ← this first deploy will fail on auth — that's fine, we're about to add env vars

### 4b. Add environment variables

Go to your project in the Vercel dashboard → **Settings → Environment Variables**.

Add the following (all environments: Production, Preview, Development):

| Name | Value |
|---|---|
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | `pk_live_...` (from Clerk — use `pk_test_` for Preview) |
| `CLERK_SECRET_KEY` | `sk_live_...` (from Clerk — use `sk_test_` for Preview) |
| `CLERK_JWKS_URL` | `https://...clerk.accounts.dev/.well-known/jwks.json` |
| `NEXT_PUBLIC_API_URL` | `https://api.yourdomain.com` |

After adding, go to **Deployments** and click **"Redeploy"** on the latest deployment.

### 4c. Set Root Directory in project settings

Go to **Settings → General → Root Directory** → set to `apps/web`

---

## Step 5 — Raspberry Pi setup

> [Full Pi deployment guide →](DEPLOYMENT.md)

### 5a. Prepare the .env file on the Pi

SSH into your Pi and:

```bash
cd ~/marketcommand
cp .env.example .env
nano .env        # fill in all values from steps 1–4 above
```

The complete Pi `.env` should look like:

```env
# Database
POSTGRES_USER=mcuser
POSTGRES_PASSWORD=your_strong_password_here

# FastAPI
DATABASE_URL=postgresql+asyncpg://mcuser:your_strong_password_here@db:5432/marketcommand
CLERK_JWKS_URL=https://<your-clerk-domain>.clerk.accounts.dev/.well-known/jwks.json
ALLOWED_ORIGINS=https://your-app.vercel.app,http://localhost:3000

# Cloudflare Tunnel
CLOUDFLARE_TUNNEL_TOKEN=eyJhXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# Optional
OPENAI_API_KEY=sk-...
RESEND_API_KEY=re_...
RESEND_FROM_EMAIL=notifications@yourdomain.com
```

### 5b. Start the stack

```bash
docker compose up -d --build
# First build takes ~5–10 min on Pi 4
```

### 5c. Verify

```bash
# API health via Docker network
curl http://localhost/health
# → {"status":"ok"}

# API health via Cloudflare Tunnel (public internet)
curl https://api.yourdomain.com/health
# → {"status":"ok"}
```

---

## Step 6 — Local development

### 6a. Copy env files

```bash
# Frontend
cp apps/web/.env.local.example apps/web/.env.local 2>/dev/null \
  || cp .env.example apps/web/.env.local

# Backend
cp .env.example apps/api/.env
```

**`apps/web/.env.local`** (frontend env file read by Next.js):
```env
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**`apps/api/.env`** (loaded by python-dotenv in uvicorn):
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/marketcommand
CLERK_JWKS_URL=https://<your-clerk-domain>.clerk.accounts.dev/.well-known/jwks.json
ALLOWED_ORIGINS=http://localhost:3000
OPENAI_API_KEY=   # optional
RESEND_API_KEY=   # optional
```

### 6b. Start local PostgreSQL

```bash
docker run -d --name pg-dev \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=marketcommand \
  -p 5432:5432 \
  postgres:16-alpine
```

### 6c. Install dependencies and run

```bash
# Install Python deps
cd apps/api && pip install -r requirements.txt

# Install Node deps
cd apps/web && npm install

# Start both (from repo root)
npm run dev
```

Open http://localhost:3000

---

## Step 7 — Optional: OpenAI integration

> **Cost:** Pay-as-you-go, ~$0.15–$0.60 / 1M tokens (gpt-4.1-mini)  
> **Sign up:** https://platform.openai.com

1. Go to https://platform.openai.com/api-keys
2. Click **"Create new secret key"**
3. Copy the key

Add to **`apps/api/.env`** (local) and **Pi `~/marketcommand/.env`**:
```env
OPENAI_API_KEY=sk-...
```

The app runs fine without this and falls back to mock agent responses automatically.

---

## Summary: order to follow

1. ✅ [Create Clerk app](https://dashboard.clerk.com) → copy `PUBLISHABLE_KEY`, `SECRET_KEY`, `JWKS_URL`
2. ✅ [Create Resend account](https://resend.com/signup) → verify domain → create API key
3. ✅ [Create Cloudflare Tunnel](https://one.dash.cloudflare.com) → set hostname `api.yourdomain.com` → copy tunnel token
4. ✅ [Deploy to Vercel](https://vercel.com/new) → set Root Directory to `apps/web` → add env vars
5. ✅ SSH into Pi → fill `.env` → `docker compose up -d --build`
6. ✅ Redeploy Vercel after all env vars are in place
7. ✅ Test end-to-end: sign in → save a strategy → check it persisted → verify email notification

---

## Where each file lives in the codebase

| What it configures | File |
|---|---|
| Frontend env (local dev) | `apps/web/.env.local` ← create from `.env.example` |
| Backend env (local dev) | `apps/api/.env` ← create from `.env.example` |
| Template for all vars | `.env.example` |
| Clerk middleware (route protection) | `apps/web/middleware.ts` |
| Clerk provider wrapper | `apps/web/app/layout.tsx` |
| Backend JWT verification | `apps/api/app/auth.py` |
| Database connection | `apps/api/app/database.py` |
| Pi full stack | `docker-compose.yml` |
| Nginx config | `deploy/nginx.conf` |
| Full deployment walkthrough | `DEPLOYMENT.md` |
