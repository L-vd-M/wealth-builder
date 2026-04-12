# Wealth Builder Deployment Guide

This repository uses a split deployment model:

- Frontend: Vercel
- Backend: Raspberry Pi running Docker Compose
- Public backend exposure: Cloudflare Tunnel

## Primary deployment references

- Raspberry Pi setup: `docs/raspberry-pi-setup.md`
- Environment setup checklist: `NEXT_STEPS.md`
- Ansible automation: `deploy/ansible/README.md`

## Production architecture

```text
Browser
  |
  | HTTPS
  v
Vercel (Next.js frontend)
  |
  | HTTPS via NEXT_PUBLIC_API_URL
  v
Cloudflare Tunnel
  |
  | HTTP
  v
Raspberry Pi
  |- nginx
  |- FastAPI
  |- PostgreSQL
```

## Required production environment values

At minimum, the Pi deployment needs these values in the root `.env` file:

- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `CLERK_JWKS_URL`
- `ALLOWED_ORIGINS`
- `CLOUDFLARE_TUNNEL_TOKEN`
- `ENCRYPTION_KEY`

Recommended for the full feature set:

- `OPENAI_API_KEY`
- `RESEND_API_KEY`
- `RESEND_FROM_EMAIL`
- `AGENT_TEMPLATES_PATH`
- `INTERNAL_API_BASE`

## Notes for the new features

- Linked trading accounts require `ENCRYPTION_KEY` because credentials are encrypted before storage.
- Agent prompt seeding expects the `project-agent-templates` repository to exist at `./project-agent-templates` on the Pi and is mounted into the API container at `/opt/project-agent-templates`.
- Scheduler jobs call internal API routes using `INTERNAL_API_BASE`, which defaults to `http://localhost:8000`.

## Minimal manual deployment flow

```bash
git clone https://github.com/L-vd-M/wealth-builder.git ~/wealth-builder
git clone https://github.com/L-vd-M/project-agent-templates.git ~/wealth-builder/project-agent-templates
cd ~/wealth-builder
cp .env.example .env
nano .env
docker compose up -d --build
```

## Update flow

```bash
cd ~/wealth-builder
git pull
docker compose up -d --build
```
