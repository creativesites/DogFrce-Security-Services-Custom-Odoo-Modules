#!/bin/sh
set -eu

if [ $# -ne 1 ]; then
  echo "usage: $0 <module_name>"
  exit 1
fi

ROOT_DIR=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
MODULE_NAME=$1

. "$SCRIPT_DIR/docker-env.sh"

if [ -f "$ROOT_DIR/.env" ]; then
  set -a
  . "$ROOT_DIR/.env"
  set +a
fi

"$COMPOSE_BIN" -f "$ROOT_DIR/deploy/docker-compose.yml" exec odoo odoo scaffold "$MODULE_NAME" /mnt/extra-addons

echo "Created module: $MODULE_NAME"
