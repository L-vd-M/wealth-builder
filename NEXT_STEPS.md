# Wealth Builder Next Steps

This document is the environment and service checklist for local development, Vercel, and Raspberry Pi deployment.

## Where values go

| Variable | Local env | Vercel | Pi `.env` |
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
| `ENCRYPTION_KEY` | ✅ | — | ✅ |
| `AGENT_TEMPLATES_PATH` | ✅ | — | ✅ |
| `INTERNAL_API_BASE` | ✅ | — | ✅ |
| `OPENAI_API_KEY` | ✅ | — | ✅ |
| `RESEND_API_KEY` | ✅ | — | ✅ |
| `RESEND_FROM_EMAIL` | ✅ | — | ✅ |

## Service links

- Clerk: https://clerk.com
- Resend: https://resend.com
- Cloudflare Zero Trust Tunnels: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
- Vercel: https://vercel.com
- Raspberry Pi setup reference: `docs/raspberry-pi-setup.md`
- Ansible setup reference: `deploy/ansible/README.md`

## Required Pi values

Fill these before running the production stack:

```env
POSTGRES_USER=mcuser
POSTGRES_PASSWORD=change_me
CLERK_JWKS_URL=https://your-clerk-domain/.well-known/jwks.json
ALLOWED_ORIGINS=https://your-vercel-domain.vercel.app,http://localhost:3000
CLOUDFLARE_TUNNEL_TOKEN=change_me
ENCRYPTION_KEY=change_me
AGENT_TEMPLATES_PATH=/opt/project-agent-templates
INTERNAL_API_BASE=http://localhost:8000
```

Optional but feature-enabling:

```env
OPENAI_API_KEY=
RESEND_API_KEY=
RESEND_FROM_EMAIL=notifications@yourdomain.com
```

## Vercel values

Set these in the Vercel project:

```env
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_...
CLERK_SECRET_KEY=sk_live_...
CLERK_JWKS_URL=https://your-clerk-domain/.well-known/jwks.json
```

## Local setup checklist

1. Copy `.env.example` to `.env`.
2. Copy `apps/api/.env.example` to `apps/api/.env`.
3. Install web dependencies with `npm install`.
4. Install API dependencies with `pip install -r apps/api/requirements.txt`.
5. Start with `npm run dev`.

## Raspberry Pi checklist

1. Flash Raspberry Pi OS Lite 64-bit and enable SSH.
2. Clone `wealth-builder` to `~/wealth-builder`.
3. Clone `project-agent-templates` to `~/wealth-builder/project-agent-templates`.
4. Copy `.env.example` to `.env` and fill all required values.
5. Start the stack with `docker compose up -d --build`.
6. Verify `curl http://localhost/health`.
7. Verify `curl https://api.yourdomain.com/health` after Cloudflare Tunnel is configured.
