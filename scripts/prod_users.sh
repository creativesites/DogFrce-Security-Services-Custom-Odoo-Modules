#!/usr/bin/env bash
# Create or update DogForce staff logins on production. Run on the server:
#
#   cd /opt/dogforce
#   bash scripts/prod_users.sh 'owner|Full Name|ceo@dogforcesecurityservices.com|replaces=kuume@dogforcesecurityservices.com'
#   bash scripts/prod_users.sh 'ops|Full Name|name@dogforcesecurityservices.com' 'hr|Full Name|name@...'
#   bash scripts/prod_users.sh --add-owner wilbert@dogforcesecurityservices.com 'finance|Full Name|name@...'
#
# Roles: ops, admin, hr, finance, manager, owner (docs/deployguard/dogforce-roles-and-pipeline.md).
# Each user gets a new random temporary password, printed once. Running it
# again for the same login updates that user and issues a new password.
# Nothing is saved unless every row is valid. See scripts/prod_users.py.

set -euo pipefail
cd "$(dirname "$0")/.."

CONTAINER="${DOGFORCE_ODOO_CONTAINER:-dogforce-prod-odoo}"
DB="${DOGFORCE_DB:-dogforce_prod}"
ADD_OWNER=""
ROWS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --add-owner) ADD_OWNER="${2:-}"; shift 2 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) ROWS+=("$1"); shift ;;
  esac
done
[ ${#ROWS[@]} -gt 0 ] || [ -n "$ADD_OWNER" ] || { sed -n '2,12p' "$0"; exit 1; }

USERS="$(printf '%s\n' "${ROWS[@]+"${ROWS[@]}"}")"
OUT="$(docker exec -i -e DG_USERS="$USERS" -e DG_ADD_OWNER="$ADD_OWNER" "$CONTAINER" \
  odoo shell --no-http -c /etc/odoo/odoo.conf -d "$DB" --log-level=error \
  < scripts/prod_users.py 2>&1)" || true

if printf '%s\n' "$OUT" | grep -q '^DG|'; then
  printf '%s\n' "$OUT" | grep '^DG|' | cut -c4-
else
  echo "The Odoo shell didn't run the script. Last lines of its output:"
  printf '%s\n' "$OUT" | tail -15
  exit 1
fi
