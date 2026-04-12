# Wealth Builder Raspberry Pi Setup

This guide is the production setup reference for running the API stack on a Raspberry Pi and hosting the frontend on Vercel.

## What this deploys

- Raspberry Pi: PostgreSQL, FastAPI, nginx, Cloudflare Tunnel via Docker Compose
- Vercel: Next.js frontend
- External services: Clerk for auth, Resend for email, Cloudflare Tunnel for secure exposure
- Optional: OpenAI for live agent deliberation responses

## Reference links

- Raspberry Pi Imager: https://www.raspberrypi.com/software/
- Raspberry Pi OS documentation: https://www.raspberrypi.com/documentation/computers/getting-started.html
- Docker Engine install docs: https://docs.docker.com/engine/install/
- Docker Compose docs: https://docs.docker.com/compose/
- Cloudflare Tunnel docs: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
- Vercel docs: https://vercel.com/docs
- Clerk docs: https://clerk.com/docs
- Resend docs: https://resend.com/docs
- Ansible docs: https://docs.ansible.com/

## Recommended hardware

- Raspberry Pi 4B or 5
- 4 GB RAM minimum
- 32 GB microSD minimum, or SSD if you want better PostgreSQL durability
- Raspberry Pi OS Lite 64-bit
- Wired ethernet preferred for stability

## Before you start

Prepare these accounts and values first:

- Clerk application keys
- Clerk JWKS URL
- Cloudflare Tunnel token
- Resend API key and sender address, if you want notifications
- Vercel project and frontend domain
- A generated Fernet encryption key for linked wallet credentials

Generate the encryption key with:

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Step 1: Flash and prepare the Pi

1. Use Raspberry Pi Imager and install Raspberry Pi OS Lite 64-bit.
2. In the Imager advanced options, enable SSH and set your username.
3. Boot the Pi and connect over SSH.
4. Update firmware and packages:

```bash
sudo apt-get update
sudo apt-get upgrade -y
```

## Step 2: Choose your setup method

You have two supported paths in this repository:

- Shell bootstrap: `deploy/setup-pi.sh`
- Ansible: `deploy/ansible/site.yml`

Use Ansible if you want a repeatable setup with a checked-in inventory and variable file.

## Step 3: Fill in the required values

If you are using Ansible, copy and edit these first:

- `deploy/ansible/inventory.example.ini`
- `deploy/ansible/group_vars/pi.example.yml`

If you are using Docker Compose directly, copy and edit:

- `.env.example` -> `.env`

Values you must replace before deployment:

- `CHANGE_ME_POSTGRES_PASSWORD`
- `CHANGE_ME_ENCRYPTION_KEY`
- `CHANGE_ME_CLERK_JWKS_URL`
- `CHANGE_ME_ALLOWED_ORIGINS`
- `CHANGE_ME_CLOUDFLARE_TUNNEL_TOKEN`
- `CHANGE_ME_FRONTEND_URL`
- `CHANGE_ME_REPO_URL`

Optional but recommended:

- `CHANGE_ME_OPENAI_API_KEY`
- `CHANGE_ME_RESEND_API_KEY`
- `CHANGE_ME_RESEND_FROM_EMAIL`

## Step 4: Clone the repositories

The production stack expects the main repository plus the prompt template repository.

```bash
git clone https://github.com/L-vd-M/wealth-builder.git ~/wealth-builder
git clone https://github.com/L-vd-M/project-agent-templates.git ~/wealth-builder/project-agent-templates
```

The template repository is mounted read-only into the API container so the seeded agent catalogue can load the original prompts.

## Step 5: Run the stack

From the repository root on the Pi:

```bash
docker compose up -d --build
```

Verify health:

```bash
curl http://localhost/health
curl http://localhost:8000/health
```

## Step 6: Verify public routing

After configuring Cloudflare Tunnel, verify:

```bash
curl https://api.yourdomain.com/health
```

Expected response:

```json
{"status":"ok"}
```

## Step 7: Point the frontend at the Pi

Set the Vercel frontend variable:

- `NEXT_PUBLIC_API_URL=https://api.yourdomain.com`

Also set the Clerk frontend variables in Vercel.

## Environment variables that matter for the new features

- `ENCRYPTION_KEY`: required for linked trading account encryption
- `AGENT_TEMPLATES_PATH`: container path for seeded agent prompts
- `INTERNAL_API_BASE`: used by scheduled cron jobs when they call internal routes
- `OPENAI_API_KEY`: enables live agent deliberation responses instead of mock responses

## Updating after deployment

```bash
cd ~/wealth-builder
git pull
docker compose up -d --build
```

If you used Ansible, rerun the playbook after updating variables or docs.

## Ansible path

See the dedicated instructions in:

- `deploy/ansible/README.md`

## Troubleshooting

- If wallet linking fails immediately, check that `ENCRYPTION_KEY` is set and valid.
- If system agents show metadata but no full prompts, make sure `project-agent-templates` exists and is mounted into the API container.
- If cron jobs do not execute, verify `INTERNAL_API_BASE=http://localhost:8000` inside the API container environment.
- If Vercel auth fails, verify Clerk keys and allowed origins.
