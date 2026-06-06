#!/bin/bash
set -e

echo "Checking if database is initialized..."

# Try to connect and check if base is installed
INITIALIZED=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -tAc \
  "SELECT COUNT(*) FROM information_schema.tables WHERE table_name='ir_module_module';" 2>/dev/null || echo "0")

if [ "$INITIALIZED" = "0" ] || [ -z "$INITIALIZED" ]; then
  echo "Database not initialized. Running first-time setup..."
  odoo --config=/etc/odoo/odoo.conf -i base --without-demo=all --stop-after-init
  echo "Initialization complete."
else
  echo "Database already initialized. Starting normally."
fi

exec odoo --config=/etc/odoo/odoo.conf
