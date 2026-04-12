#!/usr/bin/env bash
# deploy/setup-pi.sh — one-time Raspberry Pi setup script
# Run as: bash deploy/setup-pi.sh
set -euo pipefail

echo "==> Updating packages"
sudo apt-get update -y && sudo apt-get upgrade -y

echo "==> Installing Docker"
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER"

echo "==> Installing Docker Compose plugin (v2)"
sudo apt-get install -y docker-compose-plugin

echo "==> Enabling Docker on boot"
sudo systemctl enable docker
sudo systemctl start docker

echo "==> Creating project directory"
mkdir -p ~/wealth-builder
mkdir -p ~/project-agent-templates
echo "  Clone or copy this repo into ~/wealth-builder, then cd into it."
echo "  Clone project-agent-templates into ~/wealth-builder/project-agent-templates if you want built-in prompts seeded."

echo ""
echo "==> NEXT STEPS:"
echo "  1. Copy your .env file to ~/wealth-builder/.env"
echo "     (see .env.example at the repo root)"
echo "  2. Clone the templates repo into ~/wealth-builder/project-agent-templates"
echo "     git clone https://github.com/L-vd-M/project-agent-templates.git ~/wealth-builder/project-agent-templates"
echo "  3. Set ENCRYPTION_KEY in ~/wealth-builder/.env"
echo "  4. cd ~/wealth-builder"
echo "  5. docker compose up -d --build"
echo "  6. Verify: curl http://localhost/health"
echo ""
echo "==> Cloudflare Tunnel:"
echo "  Set CLOUDFLARE_TUNNEL_TOKEN in .env (see DEPLOYMENT.md for full setup)"
echo ""
echo "Done. Log out and back in for Docker group membership to take effect."
