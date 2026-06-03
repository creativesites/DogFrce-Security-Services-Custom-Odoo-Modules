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

TEST_DB="${TEST_DB:-${ODOO_DB}_test}"
MODULES="${1:-security_payroll_core,security_equipment,security_fleet}"

echo "Running Odoo tests on database '${TEST_DB}'"
echo "Modules: ${MODULES}"

"$COMPOSE_BIN" -f "$ROOT_DIR/deploy/docker-compose.yml" exec -T odoo odoo \
  -c /etc/odoo/odoo.conf \
  -d "$TEST_DB" \
  --test-enable \
  --stop-after-init \
  -i "$MODULES" \
  --log-level=test:INFO

echo "Tests finished."
