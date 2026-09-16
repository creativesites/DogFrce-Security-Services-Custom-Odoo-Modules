#!/usr/bin/env bash
# Wrapper for `npm run tauri dev` / `npm run tauri build`.
#
# Vite's VITE_* env vars (from .env / .env.<mode>) only reach the frontend
# bundle — they are NOT inherited by the Rust/Tauri process, which reads
# its own DEPLOYGUARD_* vars via std::env::var (see src-tauri/src/config.rs).
# Without this, Rust silently falls back to its compiled-in default and,
# for VITE_ODOO_DB specifically, ends up calling Odoo with db=null, which
# Odoo rejects as "Missing database name" — surfaced to the user as a
# misleading "Incorrect username or password" (see desktop/DEVIATIONS.md
# for why auth errors are collapsed like that).
#
# This script bridges the two: it reads the same .env file Vite would use
# and exports the Rust-side equivalents before invoking the Tauri CLI.
set -euo pipefail
cd "$(dirname "$0")/.."

ENV_FILE="${1:-.env}"
if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1090
  set -a
  source "$ENV_FILE"
  set +a
fi

export DEPLOYGUARD_ODOO_BASE_URL="${VITE_ODOO_BASE_URL:-${DEPLOYGUARD_ODOO_BASE_URL:-}}"
export DEPLOYGUARD_ODOO_DB="${VITE_ODOO_DB:-${DEPLOYGUARD_ODOO_DB:-}}"

echo "[dev.sh] DEPLOYGUARD_ODOO_BASE_URL=${DEPLOYGUARD_ODOO_BASE_URL:-<unset, using compiled default>}"
echo "[dev.sh] DEPLOYGUARD_ODOO_DB=${DEPLOYGUARD_ODOO_DB:-<unset — Odoo will reject with 'Missing database name' if the server hosts more than one DB>}"

exec npx tauri dev
