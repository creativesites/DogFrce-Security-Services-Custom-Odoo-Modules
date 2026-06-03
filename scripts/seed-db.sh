#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)

. "$SCRIPT_DIR/docker-env.sh"

if [ ! -f "$ROOT_DIR/.env" ]; then
  echo ".env not found. Run ./scripts/start.sh first or copy .env.example to .env"
  exit 1
fi

set -a
. "$ROOT_DIR/.env"
set +a

MODULES="security_demo_data,security_mobile,security_documents,security_accounting_controls,security_reporting"

echo "Creating/updating database '${ODOO_DB}' and installing modules..."
echo "Modules: ${MODULES}"
echo "This may take several minutes on first run."

"$COMPOSE_BIN" -f "$ROOT_DIR/deploy/docker-compose.yml" exec -T odoo odoo \
  -c /etc/odoo/odoo.conf \
  -d "$ODOO_DB" \
  -i "$MODULES" \
  --stop-after-init

echo "Database '${ODOO_DB}' is ready with demo data."
echo "Open http://localhost:${ODOO_PORT} and log in as admin / admin (default Odoo credentials)."
