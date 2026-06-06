#!/bin/bash
set -e

echo "Checking if custom modules are installed..."

INSTALLED=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -tAc \
  "SELECT COUNT(*) FROM ir_module_module WHERE name='security_base' AND state='installed';" 2>/dev/null || echo "0")

INSTALLED=$(echo $INSTALLED | tr -d '[:space:]')

if [ "$INSTALLED" != "1" ]; then
  echo "Custom modules not installed. Installing now..."
  odoo --config=/etc/odoo/odoo.conf \
    -i security_base,security_operations,security_attendance,security_leave,security_documents,security_equipment,security_fleet,security_billing,security_payroll_core,security_loans,security_discipline,security_notifications,security_reporting,security_client_reports,security_accounting_controls,security_mobile,security_shift_planner,security_l10n_na \
    --without-demo=all \
    --stop-after-init
  echo "Modules installed."
else
  echo "Custom modules already installed. Starting normally."
fi

exec odoo --config=/etc/odoo/odoo.conf
