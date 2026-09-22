#!/usr/bin/env bash
# Deploys committed origin/main to DogForce production (dogforce_prod).
#
#   bash scripts/deploy_production.sh --plan   # read-only: what's there, what would change
#   bash scripts/deploy_production.sh --go     # backup, pull, upgrade, restart, verify
#
# --go always takes a full backup first (pg_dump + filestore tarball) and
# refuses to continue if the backup is empty. Odoo is unavailable for the
# few minutes the upgrade takes.
#
# Access: key-based SSH as root. No password is stored or read here.
# Module scope: DEPLOYMENT_SCOPE_AND_EXCLUSIONS.md. The Zambia modules are
# refused outright, same blocklist as promote_staging_to_prod.sh.

set -euo pipefail

HOST="${DOGFORCE_PROD_HOST:-root@199.192.23.46}"
DB="dogforce_prod"
APP_DIR="/opt/dogforce"
# Installed if missing; everything already installed is upgraded (-u all).
NEW_MODULES="security_work,security_training,security_deployguard_bridge,security_armed_response,security_support,security_exceptions,security_telephony,security_adoption,security_tour"
EXCLUDED="security_l10n_zm security_zra_invoice security_demo_data_zm security_demo_zambia_site"

MODE="${1:-}"
[ "$MODE" = "--plan" ] || [ "$MODE" = "--go" ] || { echo "usage: $0 --plan | --go"; exit 1; }

for bad in $EXCLUDED; do
  case ",$NEW_MODULES," in *",$bad,"*) echo "refusing: $bad is excluded from production"; exit 1;; esac
done

ssh -o BatchMode=yes -o ConnectTimeout=10 "$HOST" true || {
  echo "Can't SSH to $HOST with a key. Authorise this machine's key first (see desktop/README or ask)."; exit 1; }

remote() { ssh -o BatchMode=yes "$HOST" "$@"; }

echo "==> Discovering production layout"
ODOO_C=$(remote "docker ps --format '{{.Names}}' | grep -i odoo | grep -viE 'db|postgres|whatsapp|staging' | head -1")
DB_C=$(remote "docker ps --format '{{.Names}}' | grep -iE 'db|postgres' | grep -vi staging | head -1")
echo "    odoo container: ${ODOO_C:-NOT FOUND}"
echo "    db container:   ${DB_C:-NOT FOUND}"
[ -n "$ODOO_C" ] && [ -n "$DB_C" ] || { echo "error: couldn't identify the production containers"; exit 1; }

echo "==> Code on the server"
remote "cd $APP_DIR && git rev-parse --abbrev-ref HEAD && git log -1 --oneline && git status --short | head -20"
LOCAL_CHANGES=$(remote "cd $APP_DIR && git status --porcelain --untracked-files=no | wc -l" | tr -d ' ')
git fetch -q origin
echo "    origin/main is $(git log -1 --oneline origin/main)"

echo "==> Excluded modules installed in $DB?"
INSTALLED_EXCLUDED=$(remote "docker exec $DB_C psql -U odoo -d $DB -tAc \"select name from ir_module_module where state='installed' and name in ('security_l10n_zm','security_zra_invoice','security_demo_data_zm','security_demo_zambia_site')\"" || true)
echo "    ${INSTALLED_EXCLUDED:-none}"
echo "==> Of the new modules, already installed:"
remote "docker exec $DB_C psql -U odoo -d $DB -tAc \"select name||' '||state from ir_module_module where name in ('$(echo $NEW_MODULES | sed "s/,/','/g")')\"" || true
remote "df -h $APP_DIR | tail -1"

[ "$MODE" = "--plan" ] && { echo; echo "Plan only -- nothing changed."; exit 0; }

[ "$LOCAL_CHANGES" = "0" ] || { echo "error: the server has uncommitted changes in $APP_DIR -- refusing to pull over them"; exit 1; }
[ -z "$INSTALLED_EXCLUDED" ] || { echo "error: excluded modules are installed in $DB -- stopping"; exit 1; }

TS=$(date -u +%Y%m%dT%H%M%SZ)
BK="$APP_DIR/backups/predeploy-$TS"
echo "==> Backup to $BK"
remote "mkdir -p $BK && docker exec $DB_C pg_dump -U odoo -Fc $DB > $BK/$DB.dump"
remote "docker exec $ODOO_C sh -c 'tar -czf - -C /var/lib/odoo filestore/$DB 2>/dev/null || tar -czf - -C /var/lib/odoo .' > $BK/filestore.tgz"
DUMP_SIZE=$(remote "stat -c %s $BK/$DB.dump")
echo "    dump: $DUMP_SIZE bytes"
[ "$DUMP_SIZE" -gt 100000 ] || { echo "error: backup looks empty -- stopping before touching anything"; exit 1; }

echo "==> Pull"
remote "cd $APP_DIR && git pull --ff-only origin main && git log -1 --oneline"

echo "==> Upgrade (Odoo restarts after this)"
remote "docker exec $ODOO_C odoo -c /etc/odoo/odoo.conf -d $DB -i $NEW_MODULES -u all --stop-after-init --http-port 8099 > $BK/upgrade.log 2>&1; echo exit=\$?" | tee /tmp/dg-prod-upgrade-exit.txt
remote "grep -E ' ERROR | CRITICAL ' $BK/upgrade.log | grep -v 'Importing test framework' | tail -20" || true
remote "docker restart $ODOO_C >/dev/null"

echo "==> Verify"
for i in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 https://dogforcesecurityservices.com/web/health || true)
  [ "$code" = "200" ] && break; sleep 3
done
echo "    health: $code"
remote "docker exec $DB_C psql -U odoo -d $DB -tAc \"select name||' '||state from ir_module_module where name in ('$(echo $NEW_MODULES | sed "s/,/','/g")')\""
grep -q "exit=0" /tmp/dg-prod-upgrade-exit.txt || {
  echo "!! The upgrade reported errors. Backup is at $BK. To roll back:"
  echo "   restore $BK/$DB.dump with pg_restore --clean, restore the filestore, git checkout the previous commit, restart."
  exit 1; }
echo "Done. Backup kept at $BK."
