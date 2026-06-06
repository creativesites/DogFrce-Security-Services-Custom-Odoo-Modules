#!/bin/bash
set -e

echo "Checking if database is initialized..."

# Try to connect and check if base is installed
INITIALIZED=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -tAc \
  "SELECT COUNT(*) FROM information_schema.tables WHERE table_name='ir_module_module';" 2>/dev/null || echo "0")


if [ "$INITIALIZED" = "0" ] || [ -z "$INITIALIZED" ]; then
  echo "First boot: initializing database and installing core modules..."
  odoo --config=/etc/odoo/odoo.conf \
    -i base,mail,security_base,security_operations,security_attendance,security_leave,security_documents,security_equipment,security_fleet,security_billing,security_payroll_core,security_loans,security_discipline,security_notifications,security_reporting,security_client_reports,security_accounting_controls,security_mobile,security_shift_planner,security_l10n_na \
    --without-demo=all \
    --stop-after-init
  echo "Initialization complete."
else
  echo "Database already initialized. Starting normally."
fi

exec odoo --config=/etc/odoo/odoo.conf
