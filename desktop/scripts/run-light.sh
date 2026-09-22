#!/usr/bin/env bash
# Runs the desktop app on a small-RAM Mac: build once, then launch the built
# .app -- no Vite dev server, no file watcher, no recompiling on every change.
#
# `tauri dev` keeps the Rust compiler, Vite and a watcher running alongside
# the app; on an 8 GB machine that plus Docker and an IDE fills memory. This
# pays the compile cost once (with limited parallelism so even that doesn't
# swamp the machine), then running costs only the app itself.
#
# Points at your LOCAL Odoo (http://localhost:8069, db odoo-security) --
# a normal build points at production, and test clicks shouldn't land there.
#
# Usage:
#   bash scripts/run-light.sh            # build if sources changed, then launch
#   bash scripts/run-light.sh --rebuild  # force a rebuild
#   bash scripts/run-light.sh --prod     # against PRODUCTION (real data)
#
# Trade-off: no hot reload. After changing code, run it again -- it only
# rebuilds when something under src/ or src-tauri/ is newer than the app.

set -euo pipefail

DESKTOP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$DESKTOP_DIR/src-tauri/target/debug/bundle/macos/DogForce Security Services.app"
cd "$DESKTOP_DIR"
export PATH="$HOME/.cargo/bin:$PATH"

export DEPLOYGUARD_ODOO_BASE_URL="${DEPLOYGUARD_ODOO_BASE_URL:-http://localhost:8069}"
export DEPLOYGUARD_ODOO_DB="${DEPLOYGUARD_ODOO_DB:-odoo-security}"

if [ "${1:-}" = "--prod" ]; then
  export DEPLOYGUARD_ODOO_BASE_URL="https://dogforcesecurityservices.com"
  export DEPLOYGUARD_ODOO_DB="dogforce_prod"
  echo "!!  PRODUCTION: everything you do in this app is real DogForce data."
fi

# The server is baked in at build time, so remember which one this .app was
# built for -- otherwise a later local run would silently launch a
# production build (or the reverse).
STAMP="$DESKTOP_DIR/src-tauri/target/debug/bundle/.light-target"
TARGET="$DEPLOYGUARD_ODOO_BASE_URL|$DEPLOYGUARD_ODOO_DB"

needs_build=0
if [ "${1:-}" = "--rebuild" ] || [ ! -d "$APP" ]; then
  needs_build=1
elif [ "$(cat "$STAMP" 2>/dev/null)" != "$TARGET" ]; then
  needs_build=1
elif [ -n "$(find src src-tauri/src src-tauri/tauri.conf.json src-tauri/Cargo.toml index.html -newer "$APP" -print -quit 2>/dev/null)" ]; then
  needs_build=1
fi

if [ "$needs_build" = 1 ]; then
  echo "==> Building (one-off; limited to 2 compiler jobs to keep RAM down)..."
  # 2 parallel jobs and no debug symbols: slower to compile, far lighter on
  # RAM and disk. Updater artifacts off -- those need the signing key and
  # are only for real releases (scripts/build-windows-xcompile.sh).
  CARGO_BUILD_JOBS=2 CARGO_PROFILE_DEV_DEBUG=0 \
    npx tauri build --debug --bundles app \
      --config '{"bundle":{"createUpdaterArtifacts":false}}'
  touch "$APP"
  echo "$TARGET" > "$STAMP"
fi

if ! curl -sf -o /dev/null --max-time 3 "$DEPLOYGUARD_ODOO_BASE_URL/web/health"; then
  echo "warning: local Odoo isn't answering at $DEPLOYGUARD_ODOO_BASE_URL."
  echo "         Start it with: docker start dogforce-odoo-dev-db dogforce-odoo-dev-odoo"
fi

echo "==> Launching against $DEPLOYGUARD_ODOO_BASE_URL ($DEPLOYGUARD_ODOO_DB)"
open "$APP"
