# Raspberry Pi Ansible Setup

This Ansible setup provisions a Raspberry Pi for Wealth Builder and can also deploy the Docker Compose stack.

## Files

- `site.yml`: main playbook
- `inventory.example.ini`: example inventory
- `group_vars/pi.example.yml`: values you must copy and fill in
- `templates/wealth-builder.env.j2`: generated root `.env` file

## Supported usage modes

### Run locally on the Raspberry Pi

Install Ansible first:

```bash
sudo apt-get update
sudo apt-get install -y ansible git
```

From the repository root:

```bash
cd deploy/ansible
cp inventory.example.ini inventory.ini
cp group_vars/pi.example.yml group_vars/pi.yml
ansible-playbook -i inventory.ini site.yml
```

For local execution, leave `ansible_connection=local` in the inventory.

### Run remotely from your workstation

Edit `inventory.ini` with the Pi hostname or IP, then run:

```bash
cd deploy/ansible
cp inventory.example.ini inventory.ini
cp group_vars/pi.example.yml group_vars/pi.yml
ansible-playbook -i inventory.ini site.yml
```

## Values you must change before running

Open `group_vars/pi.yml` and replace every `CHANGE_ME_...` value.

Required:

- `repo_url`
- `repo_version`
- `postgres_password`
- `clerk_jwks_url`
- `allowed_origins`
- `cloudflare_tunnel_token`
- `encryption_key`

Recommended:

- `frontend_url`
- `openai_api_key`
- `resend_api_key`
- `resend_from_email`

Optional:

- `deploy_stack: true` if you want Ansible to start the Docker stack automatically

## What the playbook does

- Installs Docker, Docker Compose plugin, git, curl, and Python tooling
- Enables Docker on boot
- Adds the deploy user to the Docker group
- Clones `wealth-builder`
- Clones `project-agent-templates` into `project-agent-templates/`
- Writes the root `.env` file from variables
- Optionally runs `docker compose up -d --build`

## After the playbook finishes

If `deploy_stack` is `false`, start manually:

```bash
cd ~/wealth-builder
docker compose up -d --build
```

Verify:

```bash
curl http://localhost/health
```
