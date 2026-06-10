#!/bin/bash
# Builds and deploys all custom modules to a remote Docker Odoo server.
#
# Usage:
#   bash scripts/deploy_modules.sh --host user@server
#   bash scripts/deploy_modules.sh --host user@server --addons /opt/odoo/custom_addons --container odoo
#
# Required:
#   --host      SSH target, e.g. ubuntu@192.168.1.100 or deploy@myserver.com
#
# Optional:
#   --addons    Remote path where modules should be extracted (default: /opt/odoo/custom_addons)
#   --container Docker container name to restart (default: odoo)
#   --db        Odoo database name to update (default: odoo — if set, runs -u all after restart)
#   --zip       Local zip to upload (default: builds fresh with build_modules_zip.sh)
#   --skip-build  Upload existing dogforce_modules.zip without rebuilding

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

SSH_HOST=""
REMOTE_ADDONS="/opt/odoo/custom_addons"
CONTAINER="odoo"
DB_NAME=""
ZIP_PATH="$PROJECT_ROOT/dogforce_modules.zip"
SKIP_BUILD=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --host|-h)       SSH_HOST="$2";         shift 2 ;;
        --addons)        REMOTE_ADDONS="$2";    shift 2 ;;
        --container)     CONTAINER="$2";        shift 2 ;;
        --db)            DB_NAME="$2";          shift 2 ;;
        --zip)           ZIP_PATH="$2";         shift 2 ;;
        --skip-build)    SKIP_BUILD=true;       shift 1 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [ -z "$SSH_HOST" ]; then
    echo "Error: --host is required."
    echo "Usage: bash scripts/deploy_modules.sh --host user@server"
    exit 1
fi

# 1. Build the zip (unless skipped)
if [ "$SKIP_BUILD" = false ]; then
    echo "==> Building modules zip..."
    bash "$SCRIPT_DIR/build_modules_zip.sh" --output "$ZIP_PATH"
    echo ""
fi

if [ ! -f "$ZIP_PATH" ]; then
    echo "Error: zip not found at $ZIP_PATH. Run without --skip-build."
    exit 1
fi

ZIP_NAME="$(basename "$ZIP_PATH")"
REMOTE_TMP="/tmp/$ZIP_NAME"

# 2. Upload
echo "==> Uploading $(du -h "$ZIP_PATH" | cut -f1) to $SSH_HOST..."
scp "$ZIP_PATH" "$SSH_HOST:$REMOTE_TMP"
echo ""

# 3. Extract + restart on remote
echo "==> Extracting and restarting Odoo on $SSH_HOST..."
ssh "$SSH_HOST" bash <<REMOTE
set -e

echo "Extracting modules to $REMOTE_ADDONS..."
sudo mkdir -p "$REMOTE_ADDONS"
sudo unzip -o "$REMOTE_TMP" -d "$REMOTE_ADDONS" > /dev/null
sudo rm -f "$REMOTE_TMP"
echo "  Extraction complete."

echo "Restarting container: $CONTAINER..."
docker restart "$CONTAINER"
echo "  Container restarted."

# Fix ownership so Odoo process can read the files
sudo chown -R 101:101 "$REMOTE_ADDONS" 2>/dev/null || true
REMOTE

echo ""
echo "==> Deployment complete."

# 4. Optionally trigger module update inside Odoo
if [ -n "$DB_NAME" ]; then
    echo ""
    echo "==> Waiting 15s for Odoo to start, then updating module list..."
    sleep 15
    ssh "$SSH_HOST" docker exec "$CONTAINER" odoo \
        --db_host=db --db_user=odoo --db_password=odoo \
        -d "$DB_NAME" --update=all --stop-after-init \
        > /dev/null 2>&1 && echo "  Module list updated." || echo "  Module update failed — update manually via Settings > Apps."
fi

echo ""
echo "Done. Visit your Odoo instance and go to Settings → Apps → Update Apps List"
echo "to see the new modules, then install them."
