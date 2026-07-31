#!/usr/bin/env bash
# ==============================================================================
# DeployGuard — Periodic / Automated Cron Deployment Runner for Alibaba Demo Server
# ==============================================================================
# Usage: Add to local crontab or automated CI/CD pipeline
# Example Crontab Entry (Every 30 minutes):
# */30 * * * * /Users/winstonzulu/Documents/GitHub/DogFrce\ Security\ Services\ Custom\ Odoo\ Modules/scripts/auto_update_demo_cron.sh >> /tmp/deploy_demo_cron.log 2>&1
# ==============================================================================

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/tmp/deploy_demo_cron_$(date +%Y%m%d_%H%M%S).log"

echo "[$(date)] Launching Automated Demo Site Update Cron..." | tee -a "${LOG_FILE}"

cd "${SCRIPT_DIR}/.."

if "${SCRIPT_DIR}/deploy_alibaba_demo.sh" >> "${LOG_FILE}" 2>&1; then
    echo "[$(date)] Automated Demo Update Completed Successfully." | tee -a "${LOG_FILE}"
else
    echo "[$(date)] ERROR: Automated Demo Update Failed. Check log at ${LOG_FILE}" | tee -a "${LOG_FILE}"
    exit 1
fi
