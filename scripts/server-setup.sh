#!/bin/bash
# DogForce Odoo Demo Server Setup
# Run this inside Alibaba WorkBench (or any Ubuntu 22.04 root shell).
# Installs Docker, deploys Odoo 19, and loads all custom modules.
#
# Usage: paste the entire file into the WorkBench terminal, or:
#   curl -sO https://raw.githubusercontent.com/creativesites/DogFrce-Security-Services-Custom-Odoo-Modules/main/scripts/server-setup.sh
#   bash server-setup.sh

set -e

PUBLIC_KEY="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINGYk5TnSl4KfoidWnUJsmgAfXudiFqHVUcrSEmJZ2Nm winston@cvmworldwide.com"
ODOO_DIR="/opt/dogforce"
MODULES_ZIP_URL="https://github.com/creativesites/DogFrce-Security-Services-Custom-Odoo-Modules/raw/main/dogforce_modules.zip"

echo "========================================"
echo " DogForce Odoo Server Setup"
echo "========================================"

# ── 1. SSH key for direct terminal access ─────────────────────────────────────
echo ""
echo "[1/7] Adding SSH key..."
mkdir -p ~/.ssh && chmod 700 ~/.ssh
grep -qxF "$PUBLIC_KEY" ~/.ssh/authorized_keys 2>/dev/null || echo "$PUBLIC_KEY" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
echo "  Done. You can now SSH directly: ssh root@47.84.205.81"

# ── 2. System update ──────────────────────────────────────────────────────────
echo ""
echo "[2/7] Updating system packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq curl unzip wget ufw

# ── 3. Install Docker ─────────────────────────────────────────────────────────
echo ""
echo "[3/7] Installing Docker..."
if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
else
    echo "  Docker already installed: $(docker --version)"
fi

# Docker Compose (plugin)
if ! docker compose version &>/dev/null; then
    apt-get install -y -qq docker-compose-plugin
fi
echo "  $(docker compose version)"

# ── 4. Firewall ───────────────────────────────────────────────────────────────
echo ""
echo "[4/7] Configuring firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp   comment "SSH"
ufw allow 80/tcp   comment "HTTP"
ufw allow 8069/tcp comment "Odoo"
ufw allow 8072/tcp comment "Odoo Longpolling"
ufw --force enable
echo "  Firewall active. Open ports: 22, 80, 8069, 8072"

# ── 5. Create directory structure ─────────────────────────────────────────────
echo ""
echo "[5/7] Setting up directory structure at $ODOO_DIR..."
mkdir -p "$ODOO_DIR"/{custom_addons,data/postgres,filestore,conf}

# odoo.conf
cat > "$ODOO_DIR/conf/odoo.conf" <<'CONF'
[options]
admin_passwd = DogForce@2026!
db_host = db
db_port = 5432
db_user = odoo
db_password = odoo_secure_2026
addons_path = /usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons
data_dir = /var/lib/odoo
db_name = dogforce-demo
proxy_mode = True
list_db = False
without_demo = False
workers = 2
CONF

# .env
cat > "$ODOO_DIR/.env" <<'ENV'
COMPOSE_PROJECT_NAME=dogforce-demo
POSTGRES_DB=postgres
POSTGRES_USER=odoo
POSTGRES_PASSWORD=odoo_secure_2026
ODOO_DB=dogforce-demo
ODOO_ADMIN_PASSWORD=DogForce@2026!
ODOO_PORT=8069
ODOO_LONGPOLLING_PORT=8072
ENV

# docker-compose.yml
cat > "$ODOO_DIR/docker-compose.yml" <<'COMPOSE'
services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U odoo"]
      interval: 10s
      timeout: 5s
      retries: 5

  odoo:
    image: odoo:19.0
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    ports:
      - "${ODOO_PORT:-8069}:8069"
      - "${ODOO_LONGPOLLING_PORT:-8072}:8072"
    volumes:
      - ./custom_addons:/mnt/extra-addons
      - ./filestore:/var/lib/odoo
      - ./conf/odoo.conf:/etc/odoo/odoo.conf
    environment:
      HOST: db
      USER: ${POSTGRES_USER}
      PASSWORD: ${POSTGRES_PASSWORD}
COMPOSE

echo "  Config files created."

# ── 6. Download and extract modules ───────────────────────────────────────────
echo ""
echo "[6/7] Downloading DogForce modules..."
TMP_ZIP="/tmp/dogforce_modules.zip"
wget -q --show-progress -O "$TMP_ZIP" "$MODULES_ZIP_URL"
unzip -o -q "$TMP_ZIP" -d "$ODOO_DIR/custom_addons/"
rm -f "$TMP_ZIP"
MODULE_COUNT=$(find "$ODOO_DIR/custom_addons" -maxdepth 1 -mindepth 1 -type d | wc -l)
echo "  $MODULE_COUNT modules extracted to $ODOO_DIR/custom_addons/"

# ── 7. Start Odoo ─────────────────────────────────────────────────────────────
echo ""
echo "[7/7] Starting Odoo..."
cd "$ODOO_DIR"
docker compose --env-file .env up -d
echo ""
echo "  Waiting for Odoo to initialise (this takes ~60 seconds on first run)..."
sleep 15

# Show status
docker compose ps

echo ""
echo "========================================"
echo " Setup Complete!"
echo "========================================"
echo ""
echo " Odoo URL:    http://47.84.205.81:8069"
echo " Master pwd:  DogForce@2026!"
echo " DB name:     dogforce-demo"
echo ""
echo " SSH access:  ssh root@47.84.205.81"
echo ""
echo " IMPORTANT: Open port 8069 in Alibaba Security Group:"
echo "   ECS Console → Security Groups → Inbound Rules → Add Rule"
echo "   Protocol: TCP  Port: 8069  Source: 0.0.0.0/0"
echo ""
echo " Logs: cd $ODOO_DIR && docker compose logs -f odoo"
