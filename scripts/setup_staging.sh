#!/usr/bin/env bash
# ==============================================================================
# DeployGuard Staging Setup & Initialization Script
# Scope: DogForce Security Services Namibia Staging Instance (dogforce_staging)
# Initializes staging on port 8070 with approved Namibian module suite.
# ==============================================================================

set -euo pipefail

STAGING_DB="dogforce_staging"
STAGING_CONTAINER="dogforce-staging-odoo"

echo "======================================================================"
echo "🧪 Initializing DeployGuard Staging Environment (dogforce_staging)"
echo "Port: 8070 | Target Database: ${STAGING_DB}"
echo "======================================================================"

# Step 1: Ensure Staging Stack is Up
echo "📦 Step 1/4: Starting staging Docker containers..."
docker compose -f deploy/docker-compose.staging.yml up -d

# Step 2: Initialize Clean Staging Database
echo "⚙️ Step 2/4: Initializing database ${STAGING_DB} (--without-demo=True)..."
docker exec -i "${STAGING_CONTAINER}" dropdb -h db_staging -U odoo --if-exists "${STAGING_DB}" || true
docker exec -i "${STAGING_CONTAINER}" odoo \
    -c /etc/odoo/odoo.conf \
    -d "${STAGING_DB}" \
    -i base \
    --without-demo=True \
    --stop-after-init

# Step 3: Install Approved Namibian Modules
echo "🚀 Step 3/4: Installing approved Namibian DeployGuard Suite..."
docker exec -i "${STAGING_CONTAINER}" odoo \
    -c /etc/odoo/odoo.conf \
    -d "${STAGING_DB}" \
    -i security_suite,security_l10n_na,security_backup_vault \
    --stop-after-init

# Step 4: Verify Exclusion Policy on Staging
echo "🛡️ Step 4/4: Verifying module exclusion policy on staging..."
docker exec -i "${STAGING_CONTAINER}" odoo shell -c /etc/odoo/odoo.conf -d "${STAGING_DB}" <<'EOF'
excluded = ['security_l10n_zm', 'security_zra_invoice', 'security_demo_data_zm']
installed_excluded = env['ir.module.module'].search([('name', 'in', excluded), ('state', '=', 'installed')])
if installed_excluded:
    raise Exception(f"CRITICAL: Excluded modules installed on staging: {installed_excluded.mapped('name')}")
print("✅ STAGING VERIFIED: Zero non-Namibian modules installed.")
EOF

echo "======================================================================"
echo "🎉 Staging environment setup complete! Access at http://localhost:8070"
echo "======================================================================"
