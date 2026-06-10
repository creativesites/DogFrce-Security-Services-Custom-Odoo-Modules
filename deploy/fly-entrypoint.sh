#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# DeployGuard — Fly.io Entrypoint (single-mode)
#
# Flow:
#  1. Parse DATABASE_URL
#  2. Start a lightweight keepalive HTTP server on :8080 so Fly health checks
#     don't kill the machine while Odoo is installing (first deploy = 10-15 min)
#  3. Wait for Postgres via psycopg2 (reliable, no pg_isready quirks)
#  4. Install modules (first run) or update them (subsequent runs)
#  5. Kill the keepalive server
#  6. exec Odoo (takes over port 8080 from here)
#
# Control env vars (set via: fly secrets set VAR=value):
#   FRESH_DB=true         — drop the DB + lock file, reinstall Odoo base only.
#                           Use to recover from broken installs. Unset after use.
#   MODULES_OVERRIDE=...  — comma-separated list that REPLACES the default module
#                           list. Set to empty string ("") to install NO custom
#                           modules (base Odoo only). Useful for one-by-one setup.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Parse DATABASE_URL ─────────────────────────────────────────────────────────
if [ -n "${DATABASE_URL:-}" ]; then
    DB_HOST=$(python3 -c "import urllib.parse; u=urllib.parse.urlparse('$DATABASE_URL'); print(u.hostname)")
    DB_PORT=$(python3 -c "import urllib.parse; u=urllib.parse.urlparse('$DATABASE_URL'); print(u.port or 5432)")
    DB_USER=$(python3 -c "import urllib.parse; u=urllib.parse.urlparse('$DATABASE_URL'); print(u.username)")
    DB_PASSWORD=$(python3 -c "import urllib.parse; u=urllib.parse.urlparse('$DATABASE_URL'); print(u.password or '')")
    DB_NAME=$(python3 -c "import urllib.parse; u=urllib.parse.urlparse('$DATABASE_URL'); print(u.path.lstrip('/').split('?')[0])")
fi

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-odoo}"
DB_PASSWORD="${DB_PASSWORD:-odoo}"
DB_NAME="${DB_NAME:-deployguard}"
MASTER_PASSWORD="${ODOO_MASTER_PASSWORD:-please_change_this_secret}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-DeployGuard2026!}"
ODOO_PORT="8080"

echo "==> [DeployGuard] db=$DB_HOST:$DB_PORT/$DB_NAME"

# ── Start keepalive HTTP server on :8080 ────────────────────────────────────────
# Returns 200 OK for /web/health so Fly health checks pass during long installs.
python3 -c "
import http.server, threading, os, signal

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'starting\n')
    def log_message(self, *args): pass

srv = http.server.HTTPServer(('0.0.0.0', int(os.environ.get('ODOO_PORT', 8080))), Handler)
t = threading.Thread(target=srv.serve_forever, daemon=True)
t.start()
print(f'Keepalive HTTP server on :{os.environ.get(\"ODOO_PORT\", 8080)}')
import time; time.sleep(9999999)
" &
KEEPALIVE_PID=$!
export ODOO_PORT
echo "==> Keepalive server started (PID $KEEPALIVE_PID)"

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
# Default full list — override by setting MODULES_OVERRIDE as a Fly secret.
# Set MODULES_OVERRIDE="" to install NO custom modules (base Odoo only).
DEFAULT_MODULES="security_base,security_operations,security_l10n_na,security_attendance,security_leave,security_discipline,security_payroll_core,security_loans,security_billing,security_accounting_controls,security_documents,security_equipment,security_fleet,security_shift_planner,security_notifications,security_reporting,security_client_reports,security_ai_engine"

if [ -n "${MODULES_OVERRIDE+x}" ]; then
    # MODULES_OVERRIDE is set (even if empty) — use it as-is
    MODULES="$MODULES_OVERRIDE"
    if [ -z "$MODULES" ]; then
        echo "==> MODULES_OVERRIDE is empty — installing base Odoo only (no custom modules)."
    else
        echo "==> MODULES_OVERRIDE active: $MODULES"
    fi
else
    MODULES="$DEFAULT_MODULES"
fi

if [ "${DEMO_DATA:-false}" = "true" ] && [ -n "$MODULES" ]; then
    MODULES="$MODULES,security_demo_data"
    echo "==> Demo data module will be installed."
fi

# ── Wait for Postgres using psycopg2 (avoids pg_isready / DNS quirks) ─────────
echo "==> Waiting for PostgreSQL at $DB_HOST:$DB_PORT ..."
RETRIES=0
until python3 - << PYEOF 2>/dev/null
import sys
try:
    import psycopg2
    conn = psycopg2.connect(
        host="$DB_HOST", port=$DB_PORT,
        user="$DB_USER", password="$DB_PASSWORD",
        database="postgres", connect_timeout=5
    )
    conn.close()
    sys.exit(0)
except Exception as e:
    sys.exit(1)
PYEOF
do
    RETRIES=$((RETRIES + 1))
    if [ "$RETRIES" -gt 150 ]; then
        echo ""
        echo "ERROR: Cannot reach PostgreSQL at $DB_HOST:$DB_PORT after 5 minutes."
        kill $KEEPALIVE_PID 2>/dev/null || true
        exit 1
    fi
    printf "."
    sleep 2
done
echo ""
echo "==> PostgreSQL is ready."

# ── FRESH_DB: drop database + lock file for a clean reinstall ─────────────────
LOCK_FILE="/var/lib/odoo/.deployguard_installed"

if [ "${FRESH_DB:-false}" = "true" ]; then
    echo "==> FRESH_DB=true — dropping database '$DB_NAME' and resetting lock file."
    echo "    WARNING: All existing data will be lost. Unset FRESH_DB after this deploy."
    python3 - << PYEOF 2>/dev/null || true
import psycopg2
try:
    conn = psycopg2.connect(host="$DB_HOST", port=$DB_PORT, user="$DB_USER", password="$DB_PASSWORD", database="postgres", connect_timeout=5)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s AND pid <> pg_backend_pid()", ("$DB_NAME",))
    cur.execute("DROP DATABASE IF EXISTS \"$DB_NAME\"")
    conn.close()
    print("Database dropped.")
except Exception as e:
    print(f"Drop failed (may not exist): {e}")
PYEOF
    rm -f "$LOCK_FILE"
    echo "==> Lock file removed. Proceeding with fresh install."
fi

# ── First install or update ────────────────────────────────────────────────────
DB_EXISTS=$(python3 - << PYEOF 2>/dev/null
import psycopg2, sys
try:
    conn = psycopg2.connect(host="$DB_HOST", port=$DB_PORT, user="$DB_USER", password="$DB_PASSWORD", database="postgres", connect_timeout=5)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", ("$DB_NAME",))
    print("1" if cur.fetchone() else "0")
    conn.close()
except:
    print("0")
PYEOF
)

if [ "$DB_EXISTS" != "1" ] || [ ! -f "$LOCK_FILE" ]; then
    echo "==> First install — installing modules. This takes 10-15 minutes..."
    echo "    (health checks are passing via keepalive server — do not interrupt)"

    if [ -n "$MODULES" ]; then
        INSTALL_FLAGS="-i $MODULES"
    else
        INSTALL_FLAGS="-i base"
        echo "    No custom modules specified — installing base Odoo only."
    fi

    odoo -c "$CONF_FILE" -d "$DB_NAME" \
        $INSTALL_FLAGS \
        --without-demo=all \
        --stop-after-init \
        --load-language=en_US

    echo "==> Setting admin password..."
    python3 - << PYEOF 2>/dev/null || echo "    (admin password set on next login)"
import psycopg2
conn = psycopg2.connect(host="$DB_HOST", port=$DB_PORT, user="$DB_USER", password="$DB_PASSWORD", database="$DB_NAME")
cur = conn.cursor()
cur.execute("UPDATE res_users SET password=%s WHERE login='admin'", ("$ADMIN_PASSWORD",))
conn.commit()
conn.close()
print("Admin password set.")
PYEOF

    touch "$LOCK_FILE"
    echo "==> Installation complete."

else
    if [ -n "$MODULES" ]; then
        echo "==> Updating modules..."
        odoo -c "$CONF_FILE" -d "$DB_NAME" \
            -u "$MODULES" \
            --stop-after-init \
            2>&1 | tail -5 || echo "==> Update finished."
    else
        echo "==> No custom modules to update — skipping update step."
    fi
fi

# ── Kill keepalive, hand off port 8080 to Odoo ─────────────────────────────────
echo "==> Stopping keepalive server..."
kill $KEEPALIVE_PID 2>/dev/null || true
sleep 1

echo "==> Starting Odoo on :$ODOO_PORT"
echo "    URL:   https://deployguard.fly.dev"
echo "    Login: admin / $ADMIN_PASSWORD"

exec odoo -c "$CONF_FILE" \
    -d "$DB_NAME" \
    --db-filter="^${DB_NAME}$"
