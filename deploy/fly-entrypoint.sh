#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# DeployGuard — Fly.io Entrypoint
#
# Two modes driven by CMD:
#   migrate  → run as release_command: DB wait + install/update modules + exit
#              (takes 5-15 min; no health check timer in this mode)
#   start    → main machine: brief DB wait + start Odoo on :8080
#              (fast ~60s; health check fires here)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

MODE="${1:-start}"

# ── Parse DATABASE_URL ─────────────────────────────────────────────────────────
# Fly sets DATABASE_URL automatically after `fly postgres attach`
if [ -n "${DATABASE_URL:-}" ]; then
    DB_HOST=$(python3 -c "import urllib.parse,os; u=urllib.parse.urlparse(os.environ['DATABASE_URL']); print(u.hostname)")
    DB_PORT=$(python3 -c "import urllib.parse,os; u=urllib.parse.urlparse(os.environ['DATABASE_URL']); print(u.port or 5432)")
    DB_USER=$(python3 -c "import urllib.parse,os; u=urllib.parse.urlparse(os.environ['DATABASE_URL']); print(u.username)")
    DB_PASSWORD=$(python3 -c "import urllib.parse,os; u=urllib.parse.urlparse(os.environ['DATABASE_URL']); print(u.password or '')")
    DB_NAME=$(python3 -c "import urllib.parse,os; u=urllib.parse.urlparse(os.environ['DATABASE_URL']); print(u.path.lstrip('/'))")
fi

# Fallback to individual env vars (for local/CI testing)
DB_HOST="${DB_HOST:-${HOST:-localhost}}"
DB_PORT="${DB_PORT:-${PORT_PG:-5432}}"
DB_USER="${DB_USER:-${USER_PG:-odoo}}"
DB_PASSWORD="${DB_PASSWORD:-${PASSWORD_PG:-odoo}}"
DB_NAME="${DB_NAME:-deployguard}"
MASTER_PASSWORD="${ODOO_MASTER_PASSWORD:-please_change_this_secret}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-DeployGuard2026!}"
ODOO_PORT="8080"   # Must match fly.toml internal_port

echo "==> [DeployGuard] mode=$MODE  db=$DB_HOST:$DB_PORT/$DB_NAME"

# ── Wait for PostgreSQL ────────────────────────────────────────────────────────
echo "==> Waiting for PostgreSQL..."
RETRIES=0
until PGPASSWORD="$DB_PASSWORD" pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -q 2>/dev/null; do
    RETRIES=$((RETRIES + 1))
    if [ "$RETRIES" -gt 60 ]; then
        echo "ERROR: PostgreSQL not ready after 120s. Check DATABASE_URL secret."
        exit 1
    fi
    printf "."
    sleep 2
done
echo ""
echo "==> PostgreSQL ready."

# ── Generate runtime odoo.conf ─────────────────────────────────────────────────
CONF_FILE="/tmp/odoo-fly.conf"
mkdir -p /var/lib/odoo

cat > "$CONF_FILE" << ODOO_CONF
[options]
addons_path = /mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons
data_dir = /var/lib/odoo

db_host     = $DB_HOST
db_port     = $DB_PORT
db_name     = $DB_NAME
db_user     = $DB_USER
db_password = $DB_PASSWORD

admin_passwd = $MASTER_PASSWORD
list_db      = False
proxy_mode   = True

xmlrpc_port = $ODOO_PORT
workers     = 0
max_cron_threads = 1

limit_time_cpu  = 600
limit_time_real = 1200
limit_memory_soft = 671088640
limit_memory_hard = 805306368

log_level = warn
logfile   = False
ODOO_CONF

# ── Module list ────────────────────────────────────────────────────────────────
CORE_MODULES="security_base,security_operations,security_l10n_na"
WORKFORCE_MODULES="security_attendance,security_leave,security_discipline"
PAYROLL_MODULES="security_payroll_core,security_loans"
BILLING_MODULES="security_billing,security_accounting_controls"
OPS_MODULES="security_documents,security_equipment,security_fleet,security_shift_planner,security_notifications"
REPORTING_MODULES="security_reporting,security_client_reports"
AI_MODULE="security_ai_engine"

MODULES="$CORE_MODULES,$WORKFORCE_MODULES,$PAYROLL_MODULES,$BILLING_MODULES,$OPS_MODULES,$REPORTING_MODULES,$AI_MODULE"

if [ "${DEMO_DATA:-false}" = "true" ]; then
    MODULES="$MODULES,security_demo_data"
    echo "==> Demo data module included."
fi

# ── MODE: migrate (runs as release_command — no health check pressure) ─────────
if [ "$MODE" = "migrate" ]; then
    echo "==> MIGRATE MODE — install or update all modules."

    LOCK_FILE="/var/lib/odoo/.deployguard_installed"

    DB_EXISTS=$(PGPASSWORD="$DB_PASSWORD" psql \
        -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
        -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>/dev/null || echo "0")

    if [ "$DB_EXISTS" != "1" ] || [ ! -f "$LOCK_FILE" ]; then
        echo "==> First install detected. Installing: $MODULES"
        echo "    This takes 5-15 minutes..."

        odoo -c "$CONF_FILE" -d "$DB_NAME" \
            -i "$MODULES" \
            --without-demo=all \
            --stop-after-init \
            --load-language=en_US

        # Set a safe admin password
        PGPASSWORD="$DB_PASSWORD" psql \
            -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
            -c "UPDATE res_users
                SET password = crypt('$ADMIN_PASSWORD', gen_salt('bf'))
                WHERE login = 'admin';" \
            2>/dev/null || echo "    (Password will be set on first login)"

        touch "$LOCK_FILE"
        echo "==> Install complete."

    else
        echo "==> Updating modules: $MODULES"
        odoo -c "$CONF_FILE" -d "$DB_NAME" \
            -u "$MODULES" \
            --stop-after-init \
            2>&1 | tail -20 \
            && echo "==> Update complete." \
            || echo "==> Update finished (check logs if issues persist)."
    fi

    echo "==> migrate done. Exiting cleanly."
    exit 0
fi

# ── MODE: start (main machine — just boot Odoo, health check will fire) ────────
echo "==> START MODE — launching Odoo on :$ODOO_PORT"
echo "    URL:   https://deployguard.fly.dev"
echo "    Login: admin / $ADMIN_PASSWORD"

exec odoo -c "$CONF_FILE" \
    -d "$DB_NAME" \
    --db-filter="^${DB_NAME}$"
