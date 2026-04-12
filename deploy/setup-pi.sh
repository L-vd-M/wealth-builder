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
mkdir -p ~/marketcommand
echo "  Clone or copy this repo into ~/marketcommand, then cd into it."

echo ""
echo "==> NEXT STEPS:"
echo "  1. Copy your .env file to ~/marketcommand/.env"
echo "     (see .env.example at the repo root)"
echo "  2. cd ~/marketcommand"
echo "  3. docker compose up -d --build"
echo "  4. Verify: curl http://localhost/health"
echo ""
echo "==> Cloudflare Tunnel:"
echo "  Set CLOUDFLARE_TUNNEL_TOKEN in .env (see DEPLOYMENT.md for full setup)"
echo ""
echo "Done. Log out and back in for Docker group membership to take effect."
