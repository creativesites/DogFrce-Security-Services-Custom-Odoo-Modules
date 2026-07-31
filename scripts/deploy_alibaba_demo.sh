#!/usr/bin/env bash
# ==============================================================================
# DeployGuard — Alibaba Cloud Demo Site 1-Click Automated Deployment Script
# ==============================================================================
# Target Host: 47.84.205.81 (Alibaba Cloud Singapore Node)
# Databases: zambia-demo & dogforce_dev
# Meta-Module: security_demo_zambia_site
# ==============================================================================

set -eo pipefail

SERVER_IP="47.84.205.81"
SERVER_USER="root"
SSH_KEY_PATH="/Users/winstonzulu/Documents/GitHub/Personal-Assistant/.deploy-local/claude-local.pem"
REMOTE_PATH="/opt/dogforce/custom_addons/"
CONTAINER_NAME="dogforce-demo-odoo"

echo "======================================================================"
echo "🚀 DeployGuard — Starting Automated Deployment to Alibaba Cloud Demo Server"
echo "   Target Server: ${SERVER_IP}"
echo "   Demo Databases: zambia-demo, dogforce_dev"
echo "======================================================================"

# ------------------------------------------------------------------------------
# STEP 1: Sync Clean Custom Addons
# ------------------------------------------------------------------------------
echo "📦 Step 1: Syncing clean custom_addons directory..."
rsync -avz --delete \
  -e "ssh -i ${SSH_KEY_PATH} -o ConnectTimeout=30 -o ServerAliveInterval=15" \
  --exclude='.git*' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  ./custom_addons/ \
  ${SERVER_USER}@${SERVER_IP}:${REMOTE_PATH}

echo "✅ Custom Addons synced successfully."

# ------------------------------------------------------------------------------
# STEP 2: Pre-Flight Module Exclusion Audit
# ------------------------------------------------------------------------------
echo "🛡️ Step 2: Executing Pre-Flight Module Exclusion Audit..."
sleep 1
EXCLUDED_FOUND=$(ssh -i ${SSH_KEY_PATH} -o ConnectTimeout=30 -o ServerAliveInterval=15 ${SERVER_USER}@${SERVER_IP} \
  "docker exec -i dogforce-demo-db psql -U odoo -d zambia-demo -t -A -c \"SELECT name FROM ir_module_module WHERE name IN ('security_l10n_na', 'security_demo_data') AND state = 'installed';\"" || true)

if [ -n "${EXCLUDED_FOUND}" ]; then
    echo "❌ CRITICAL: Pre-Flight Audit Failed! Prohibited Namibian modules found on database: ${EXCLUDED_FOUND}"
    exit 1
fi
echo "✅ Pre-Flight Audit Passed: No Namibian modules active on demo database."

# ------------------------------------------------------------------------------
# STEP 3: Upgrade zambia-demo Database
# ------------------------------------------------------------------------------
echo "🔄 Step 3: Upgrading 'zambia-demo' database via security_demo_zambia_site..."
ssh -i ${SSH_KEY_PATH} -o ConnectTimeout=30 -o ServerAliveInterval=15 ${SERVER_USER}@${SERVER_IP} \
  "docker exec -i ${CONTAINER_NAME} odoo -d zambia-demo -i security_demo_zambia_site -u security_suite,security_demo_zambia_site --stop-after-init"

echo "✅ 'zambia-demo' database upgrade completed."

# ------------------------------------------------------------------------------
# STEP 4: Upgrade dogforce_dev Database
# ------------------------------------------------------------------------------
echo "🔄 Step 4: Upgrading 'dogforce_dev' database via security_demo_zambia_site..."
ssh -i ${SSH_KEY_PATH} -o ConnectTimeout=30 -o ServerAliveInterval=15 ${SERVER_USER}@${SERVER_IP} \
  "docker exec -i ${CONTAINER_NAME} odoo -d dogforce_dev -i security_demo_zambia_site -u security_suite,security_demo_zambia_site --stop-after-init"

echo "✅ 'dogforce_dev' database upgrade completed."

# ------------------------------------------------------------------------------
# STEP 5: Restart Docker Container
# ------------------------------------------------------------------------------
echo "🔄 Step 5: Restarting Odoo Docker Container (${CONTAINER_NAME})..."
ssh -i ${SSH_KEY_PATH} -o ConnectTimeout=30 -o ServerAliveInterval=15 ${SERVER_USER}@${SERVER_IP} "docker restart ${CONTAINER_NAME}"

echo "⏳ Waiting 5 seconds for web server initialization..."
sleep 5

# ------------------------------------------------------------------------------
# STEP 6: Live Health Check
# ------------------------------------------------------------------------------
echo "🌐 Step 6: Performing Live HTTP Health Check against http://${SERVER_IP}:8069/web..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://${SERVER_IP}:8069/web || true)

if [ "${HTTP_CODE}" == "200" ] || [ "${HTTP_CODE}" == "303" ]; then
    echo "======================================================================"
    echo "🎉 SUCCESS: DeployGuard Alibaba Cloud Demo Server Deployment Completed!"
    echo "   HTTP Status: ${HTTP_CODE}"
    echo "   Demo Portal: http://${SERVER_IP}:8069/web"
    echo "======================================================================"
else
    echo "⚠️ WARNING: HTTP Health Check returned status ${HTTP_CODE}. Check container logs."
    ssh -i ${SSH_KEY_PATH} ${SERVER_USER}@${SERVER_IP} "docker logs --tail 30 ${CONTAINER_NAME}"
    exit 1
fi
