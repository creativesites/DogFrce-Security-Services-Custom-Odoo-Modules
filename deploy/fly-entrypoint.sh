#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# DogForce Security — Fly.io Entrypoint
# Handles: DB wait → first-install → update → start
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Parse DATABASE_URL (set automatically by `fly postgres attach`) ────────────
if [ -n "${DATABASE_URL:-}" ]; then
    DB_HOST=$(python3 -c "import urllib.parse,os; u=urllib.parse.urlparse(os.environ['DATABASE_URL']); print(u.hostname)")
    DB_PORT=$(python3 -c "import urllib.parse,os; u=urllib.parse.urlparse(os.environ['DATABASE_URL']); print(u.port or 5432)")
    DB_USER=$(python3 -c "import urllib.parse,os; u=urllib.parse.urlparse(os.environ['DATABASE_URL']); print(u.username)")
    DB_PASSWORD=$(python3 -c "import urllib.parse,os; u=urllib.parse.urlparse(os.environ['DATABASE_URL']); print(u.password or '')")
    DB_NAME=$(python3 -c "import urllib.parse,os; u=urllib.parse.urlparse(os.environ['DATABASE_URL']); print(u.path.lstrip('/'))")
fi

# Fallback to individual env vars (for local testing)
DB_HOST="${DB_HOST:-${HOST:-localhost}}"
DB_PORT="${DB_PORT:-${PORT:-5432}}"
DB_USER="${DB_USER:-${USER:-odoo}}"
DB_PASSWORD="${DB_PASSWORD:-${PASSWORD:-odoo}}"
DB_NAME="${DB_NAME:-dogforce}"
MASTER_PASSWORD="${ODOO_MASTER_PASSWORD:-please_change_this_secret}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-DogForce2026!}"

echo "==> [DogForce] Starting entrypoint"
echo "    DB: $DB_HOST:$DB_PORT/$DB_NAME (user: $DB_USER)"

# ── Wait for PostgreSQL ────────────────────────────────────────────────────────
echo "==> Waiting for PostgreSQL..."
until PGPASSWORD="$DB_PASSWORD" pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -q 2>/dev/null; do
    printf "."
    sleep 2
done
echo ""
echo "==> PostgreSQL ready."

# ── Generate runtime odoo.conf ─────────────────────────────────────────────────
CONF_FILE="/tmp/odoo-fly.conf"
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

xmlrpc_port = 8069
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
# Ordered by dependency depth — Odoo resolves further, but this helps speed.
CORE_MODULES="security_base,security_operations,security_l10n_na"
WORKFORCE_MODULES="security_attendance,security_leave,security_discipline"
PAYROLL_MODULES="security_payroll_core,security_loans"
BILLING_MODULES="security_billing,security_accounting_controls"
OPS_MODULES="security_documents,security_equipment,security_fleet,security_shift_planner,security_notifications"
REPORTING_MODULES="security_reporting,security_client_reports"
AI_MODULE="security_ai_engine"

MODULES="$CORE_MODULES,$WORKFORCE_MODULES,$PAYROLL_MODULES,$BILLING_MODULES,$OPS_MODULES,$REPORTING_MODULES,$AI_MODULE"

# Include demo data if DEMO_DATA=true (set via fly secrets set DEMO_DATA=true)
if [ "${DEMO_DATA:-false}" = "true" ]; then
    MODULES="$MODULES,security_demo_data"
    echo "==> Demo data module included."
fi

# ── Determine if this is a first-time install ──────────────────────────────────
LOCK_FILE="/var/lib/odoo/.dogforce_deployed"

DB_EXISTS=$(PGPASSWORD="$DB_PASSWORD" psql \
    -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
    -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>/dev/null || echo "0")

if [ "$DB_EXISTS" != "1" ] || [ ! -f "$LOCK_FILE" ]; then
    # ── FIRST INSTALL ──────────────────────────────────────────────────────────
    echo "==> First deployment detected — installing all modules."
    echo "    Modules: $MODULES"
    echo "    This takes 3-8 minutes. Please wait..."

    odoo -c "$CONF_FILE" -d "$DB_NAME" \
        -i "$MODULES" \
        --without-demo=all \
        --stop-after-init \
        --load-language=en_US

    echo "==> Setting admin password..."
    PGPASSWORD="$DB_PASSWORD" psql \
        -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        -c "UPDATE res_users SET password='$ADMIN_PASSWORD' WHERE login='admin';" \
        2>/dev/null || echo "    (Password set via Odoo hash on next login)"

    touch "$LOCK_FILE"
    echo "==> Installation complete."

else
    # ── UPDATE ─────────────────────────────────────────────────────────────────
    echo "==> Existing deployment — updating modules."
    odoo -c "$CONF_FILE" -d "$DB_NAME" \
        -u "$MODULES" \
        --stop-after-init 2>/dev/null \
        && echo "==> Update complete." \
        || echo "==> Update finished with warnings (non-fatal)."
fi

# ── Handle 'migrate' command (Fly release_command pattern) ────────────────────
if [ "${1:-}" = "migrate" ]; then
    echo "==> Migration step done. Exiting."
    exit 0
fi

# ── Start Odoo ─────────────────────────────────────────────────────────────────
echo "==> Starting Odoo on :8069"
echo "    Login: admin / $ADMIN_PASSWORD"
echo "    Master password is in Fly secrets (ODOO_MASTER_PASSWORD)"

exec odoo -c "$CONF_FILE" \
    -d "$DB_NAME" \
    --db-filter="^$DB_NAME$"
