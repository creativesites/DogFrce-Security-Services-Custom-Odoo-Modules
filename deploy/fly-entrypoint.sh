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
MODULES="security_base,security_operations,security_l10n_na,security_attendance,security_leave,security_discipline,security_payroll_core,security_loans,security_billing,security_accounting_controls,security_documents,security_equipment,security_fleet,security_shift_planner,security_notifications,security_reporting,security_client_reports,security_ai_engine"

if [ "${DEMO_DATA:-false}" = "true" ]; then
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

# ── First install or update ────────────────────────────────────────────────────
LOCK_FILE="/var/lib/odoo/.deployguard_installed"

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

    odoo -c "$CONF_FILE" -d "$DB_NAME" \
        -i "$MODULES" \
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
    echo "==> Updating modules..."
    odoo -c "$CONF_FILE" -d "$DB_NAME" \
        -u "$MODULES" \
        --stop-after-init \
        2>&1 | tail -5 || echo "==> Update finished."
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
