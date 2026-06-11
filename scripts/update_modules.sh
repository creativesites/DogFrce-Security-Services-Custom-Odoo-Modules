#!/bin/bash
# Push changed modules to the demo server and hot-reload them.
#
# Usage:
#   bash scripts/update_modules.sh security_theme security_demo_site
#   bash scripts/update_modules.sh --all
#   bash scripts/update_modules.sh --all --no-restart

set -e

SERVER="root@47.84.205.81"
REMOTE_ADDONS="/opt/dogforce/custom_addons"
CONTAINER="dogforce-demo-odoo-1"
DB="dogforce-demo"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADDONS_DIR="$(cd "$SCRIPT_DIR/../custom_addons" && pwd)"

MODULES=()
UPDATE_ALL=false
NO_RESTART=false

for arg in "$@"; do
    case "$arg" in
        --all)       UPDATE_ALL=true ;;
        --no-restart) NO_RESTART=true ;;
        --*)         echo "Unknown option: $arg"; exit 1 ;;
        *)           MODULES+=("$arg") ;;
    esac
done

if $UPDATE_ALL; then
    MODULES=($(find "$ADDONS_DIR" -maxdepth 1 -mindepth 1 -type d -exec test -f '{}/__manifest__.py' \; -print | xargs -I{} basename {}))
fi

if [ ${#MODULES[@]} -eq 0 ]; then
    echo "Usage: bash scripts/update_modules.sh <module1> [module2 ...] [--all] [--no-restart]"
    exit 1
fi

echo "==> Syncing ${#MODULES[@]} module(s) to $SERVER..."
for mod in "${MODULES[@]}"; do
    src="$ADDONS_DIR/$mod"
    if [ ! -d "$src" ]; then
        echo "  WARNING: $mod not found at $src, skipping"
        continue
    fi
    rsync -az --delete \
        --exclude='__pycache__' --exclude='*.pyc' --exclude='.DS_Store' \
        "$src/" "$SERVER:$REMOTE_ADDONS/$mod/"
    echo "  ✓ $mod"
done

if $NO_RESTART; then
    echo ""
    echo "Skipped restart (--no-restart). Run manually:"
    echo "  ssh $SERVER 'docker restart $CONTAINER'"
    exit 0
fi

# Build comma-separated list for -u flag
MOD_LIST=$(IFS=','; echo "${MODULES[*]}")

echo ""
echo "==> Restarting Odoo with -u $MOD_LIST..."
ssh "$SERVER" bash <<REMOTE
set -e
docker restart $CONTAINER
echo "  Waiting 20s for startup..."
sleep 20
STATUS=\$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8069/web/health)
echo "  Health check: HTTP \$STATUS"
REMOTE

echo ""
echo "Done. Visit: http://47.84.205.81:8069"
echo ""
echo "Tip: If modules need schema changes, run inside WorkBench:"
echo "  docker exec $CONTAINER odoo -d $DB -u $MOD_LIST --stop-after-init"
