#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
BACKUP_DIR="$ROOT_DIR/.local/backups"

. "$SCRIPT_DIR/docker-env.sh"

if [ ! -f "$ROOT_DIR/.env" ]; then
  echo ".env not found. Copy .env.example to .env first."
  exit 1
fi

mkdir -p "$BACKUP_DIR"

DB_NAME=$(grep '^ODOO_DB=' "$ROOT_DIR/.env" | cut -d '=' -f 2-)
DB_USER=$(grep '^POSTGRES_USER=' "$ROOT_DIR/.env" | cut -d '=' -f 2-)
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_FILE="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql"

set -a
. "$ROOT_DIR/.env"
set +a

"$COMPOSE_BIN" -f "$ROOT_DIR/deploy/docker-compose.yml" exec -T db pg_dump -U "$DB_USER" "$DB_NAME" > "$OUTPUT_FILE"

echo "Backup written to $OUTPUT_FILE"
