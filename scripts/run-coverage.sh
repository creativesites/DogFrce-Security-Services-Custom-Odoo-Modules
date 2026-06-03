#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)

. "$SCRIPT_DIR/docker-env.sh"

if [ ! -f "$ROOT_DIR/.env" ]; then
  echo ".env not found. Run ./scripts/start.sh first"
  exit 1
fi

set -a
. "$ROOT_DIR/.env"
set +a

TEST_DB="${TEST_DB:-${ODOO_DB}_test}"
MODULES="${1:-security_payroll_core}"
REPORT_DIR="${ROOT_DIR}/.local/coverage"

mkdir -p "$REPORT_DIR"

echo "Installing coverage.py in Odoo container (one-time per container rebuild)..."
"$COMPOSE_BIN" -f "$ROOT_DIR/deploy/docker-compose.yml" exec -T odoo \
  pip install --quiet coverage 2>/dev/null || true

echo "Running tests with coverage on database '${TEST_DB}'"
echo "Modules: ${MODULES}"

"$COMPOSE_BIN" -f "$ROOT_DIR/deploy/docker-compose.yml" exec -T odoo sh -c "
  coverage erase &&
  coverage run --source=/mnt/extra-addons/${MODULES%%,*} \
    odoo -c /etc/odoo/odoo.conf \
      -d '${TEST_DB}' \
      --test-enable \
      --stop-after-init \
      -i '${MODULES}' \
      --log-level=test:INFO &&
  coverage html -d /var/lib/odoo/coverage_html &&
  coverage report
"

"$COMPOSE_BIN" -f "$ROOT_DIR/deploy/docker-compose.yml" cp \
  "${COMPOSE_PROJECT_NAME:-dogforce-odoo-dev}-odoo:/var/lib/odoo/coverage_html" \
  "$REPORT_DIR/html" 2>/dev/null || \
  echo "Note: copy html report manually from container /var/lib/odoo/coverage_html"

echo ""
echo "Coverage report: ${REPORT_DIR}/html/index.html"
echo "Open with: open ${REPORT_DIR}/html/index.html"
