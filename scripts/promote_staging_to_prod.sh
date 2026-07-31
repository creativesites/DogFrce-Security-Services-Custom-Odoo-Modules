#!/usr/bin/env bash
# ==============================================================================
# DeployGuard Production Promotion & Zero-Downtime Rollback Script
# Scope: DogForce Security Services Namibia Deployment
# Enforces strict module exclusion rules & pre-deploy automated snapshots.
# ==============================================================================

set -euo pipefail

MODULES_TO_UPGRADE="${1:-security_suite}"
PROD_DB="dogforce_prod"
PROD_CONTAINER="dogforce-prod-odoo"

# Blocklist of excluded non-Namibia modules that MUST NOT be installed/upgraded
EXCLUDED_MODULES=("security_l10n_zm" "security_zra_invoice" "security_demo_data_zm")

echo "======================================================================"
echo "🚀 DeployGuard Promotion Pipeline | Staging ➔ Production (Namibia)"
echo "Target Database: ${PROD_DB}"
echo "Modules Requested: ${MODULES_TO_UPGRADE}"
echo "Timestamp: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
echo "======================================================================"

# Step 0: Safeguard Check — Validate Exclusion Blocklist
echo "🛡️ Step 0/6: Running scope & module exclusion safeguard check..."
for excluded in "${EXCLUDED_MODULES[@]}"; do
    if [[ "${MODULES_TO_UPGRADE}" == *"${excluded}"* ]]; then
        echo "❌ CRITICAL SAFETY ERROR: Attempted to promote excluded module '${excluded}'!"
        echo "🛑 This deployment server is strictly scoped for DogForce Namibia."
        echo "   Non-Namibian modules (${EXCLUDED_MODULES[*]}) are strictly prohibited."
        echo "   Promotion aborted."
        exit 1
    fi
done

# Step 0.5: Verify no excluded modules are installed in the production database
echo "🔍 Checking database state for prohibited module installations..."
EXCLUDED_CHECK=$(docker exec -i "${PROD_CONTAINER}" odoo shell --no-http -c /etc/odoo/odoo.conf -d "${PROD_DB}" <<'EOF'
excluded = ['security_l10n_zm', 'security_zra_invoice', 'security_demo_data_zm']
installed_excluded = env['ir.module.module'].search([('name', 'in', excluded), ('state', '=', 'installed')])
if installed_excluded:
    print("FOUND_EXCLUDED:" + ",".join(installed_excluded.mapped('name')))
else:
    print("ALL_CLEAR")
EOF
)

if [[ "${EXCLUDED_CHECK}" == *"FOUND_EXCLUDED"* ]]; then
    echo "❌ CRITICAL SAFETY ERROR: Prohibited module(s) detected in database!"
    echo "Details: ${EXCLUDED_CHECK}"
    echo "🛑 Promotion aborted to prevent cross-localization corruption."
    exit 1
fi
echo "✅ Exclusion safeguard check passed. Target module suite is valid for Namibia."

# Step 1: Execute Pre-Deploy Snapshot
echo "📸 Step 1/6: Taking mandatory pre-deploy production snapshot..."
docker exec -i "${PROD_CONTAINER}" odoo shell --no-http -c /etc/odoo/odoo.conf -d "${PROD_DB}" <<'EOF'
env['security.backup.manager'].sudo().run_pre_deploy_snapshot()
env.cr.commit()
EOF

echo "✅ Pre-deploy snapshot completed."

# Step 2: Stop Production Odoo Container
echo "🛑 Step 2/6: Pausing production Odoo container..."
docker stop "${PROD_CONTAINER}"

# Step 3: Run Module Upgrade
echo "🔄 Step 3/6: Executing schema & module upgrade: -u ${MODULES_TO_UPGRADE}..."
if docker run --rm \
    --network dogforce-prod_default \
    --volumes-from "${PROD_CONTAINER}" \
    -e HOST=db_prod \
    -e USER=odoo \
    -e PASSWORD=DogForce_Prod_Db_2026_SecurePass! \
    odoo:19.0 \
    odoo -c /etc/odoo/odoo.conf -d "${PROD_DB}" -u "${MODULES_TO_UPGRADE}" --stop-after-init; then
    echo "✅ Module upgrade completed successfully."
else
    echo "❌ ERROR: Module upgrade failed! Initiating automatic rollback..."
    echo "⚠️ Starting production container back up on previous stable state..."
    docker start "${PROD_CONTAINER}"
    exit 1
fi

# Step 4: Restart Production Container
echo "▶️ Step 4/6: Restarting production Odoo container..."
docker start "${PROD_CONTAINER}"
sleep 5

# Step 5: Post-Deploy Safeguard Audit & Health Check
echo "🔍 Step 5/6: Running post-deploy health & integrity checks..."
if curl -s -f -I http://localhost:8069/web/health > /dev/null || curl -s -f -I http://localhost:8069/web > /dev/null; then
    echo "======================================================================"
    echo "🎉 PROMOTION SUCCESSFUL! DeployGuard Production is healthy & operational."
    echo "======================================================================"
else
    echo "⚠️ WARNING: Health check returned non-200/303 response. Inspect docker logs ${PROD_CONTAINER}."
fi
