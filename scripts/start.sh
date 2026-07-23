#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)

. "$SCRIPT_DIR/docker-env.sh"

if [ ! -f "$ROOT_DIR/.env" ]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
  echo "Created $ROOT_DIR/.env from .env.example"
fi

set -a
. "$ROOT_DIR/.env"
set +a

mkdir -p \
  "$ROOT_DIR/.local/postgres" \
  "$ROOT_DIR/.local/odoo" \
  "$ROOT_DIR/.local/whatsapp_session" \
  "$ROOT_DIR/custom_addons"


cat > "$ROOT_DIR/.local/odoo.conf" <<EOF
[options]
admin_passwd = ${ODOO_ADMIN_PASSWORD}
db_host = db
db_port = 5432
db_user = ${POSTGRES_USER}
db_password = ${POSTGRES_PASSWORD}
addons_path = /usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons
data_dir = /var/lib/odoo
proxy_mode = False
list_db = True
without_demo = False
EOF

"$COMPOSE_BIN" -f "$ROOT_DIR/deploy/docker-compose.yml" up -d

echo "Odoo starting on http://localhost:8069"
