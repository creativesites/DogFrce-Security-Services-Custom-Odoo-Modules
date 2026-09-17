#!/bin/bash
set -e

# Generate /etc/odoo/odoo.conf from template if template exists and config does not
if [ -f /etc/odoo/odoo.conf.template ] && [ ! -f /etc/odoo/odoo.conf ]; then
  python3 -c "
import os
template_path = '/etc/odoo/odoo.conf.template'
target_path = '/etc/odoo/odoo.conf'
with open(template_path, 'r') as f:
    content = f.read()

defaults = {
    'ADMIN_PASSWD': os.environ.get('ADMIN_PASSWD', 'admin123'),
    'DB_HOST': os.environ.get('HOST', os.environ.get('DB_HOST', 'db')),
    'DB_PORT': os.environ.get('PORT', os.environ.get('DB_PORT', '5432')),
    'DB_USER': os.environ.get('USER', os.environ.get('DB_USER', 'odoo')),
    'DB_PASSWORD': os.environ.get('PASSWORD', os.environ.get('DB_PASSWORD', '')),
    'DB_NAME': os.environ.get('DB_NAME', 'dogforce_prod'),
    'HTTP_PORT': os.environ.get('HTTP_PORT', '8069'),
    'LOG_LEVEL': os.environ.get('LOG_LEVEL', 'info'),
}
for key, val in defaults.items():
    content = content.replace(f'\${{{key}}}', str(val))

with open(target_path, 'w') as f:
    f.write(content)
"
fi

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
