#!/usr/bin/env bash
# Cross-compiles a portable Windows .exe from macOS via cargo-xwin.
#
# This is a fallback for when the normal path (GitHub Actions Windows
# runner, see .github/workflows/desktop-build.yml) isn't available. It
# produces a single portable .exe, NOT an NSIS/MSI installer — WiX/NSIS
# bundling from macOS is its own can of worms, not attempted here. Prefer
# real CI or an actual Windows machine once either is available again;
# this exists to unblock a pilot build in the meantime.
#
# One-time setup this script assumes has already been done:
#   rustup target add x86_64-pc-windows-msvc
#   cargo install --locked cargo-xwin
#   brew install llvm   # ring/rustls need `llvm-lib` to cross-link for
#                        # MSVC; cc-rs errors with "failed to find tool
#                        # llvm-lib" without it. rustup's own
#                        # `llvm-tools` component does NOT provide this
#                        # (only llvm-ar, an ELF-style archiver) — has to
#                        # be the full Homebrew llvm.
#
# Usage:
#   bash scripts/build-windows-xcompile.sh
#
# Production only. DogForce's staging Odoo (dogforce_staging) only listens
# on localhost:8070 on the production host itself (see
# DEPLOYMENT_SCOPE_AND_EXCLUSIONS.md) -- there's no public staging URL a
# desktop app on an arbitrary Windows machine could reach, so this script
# doesn't offer a staging mode. Override DEPLOYGUARD_ODOO_BASE_URL/_DB
# yourself if you genuinely need to point at something else.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT_DIR="$DESKTOP_DIR/dist-windows"

export DEPLOYGUARD_ODOO_BASE_URL="${DEPLOYGUARD_ODOO_BASE_URL:-https://dogforcesecurityservices.com}"
export DEPLOYGUARD_ODOO_DB="${DEPLOYGUARD_ODOO_DB:-dogforce_prod}"

echo "==> Building against \$DEPLOYGUARD_ODOO_BASE_URL=$DEPLOYGUARD_ODOO_BASE_URL"

if ! command -v llvm-lib >/dev/null 2>&1; then
  export PATH="/opt/homebrew/opt/llvm/bin:$PATH"
fi
if ! command -v llvm-lib >/dev/null 2>&1; then
  echo "error: llvm-lib not found. Run: brew install llvm"
  exit 1
fi

cd "$DESKTOP_DIR"
npx tauri build --target x86_64-pc-windows-msvc --runner cargo-xwin --no-bundle

BIN="$DESKTOP_DIR/src-tauri/target/x86_64-pc-windows-msvc/release/deployguard-desktop.exe"
if [ ! -f "$BIN" ]; then
  echo "error: build did not produce $BIN"
  exit 1
fi

mkdir -p "$OUT_DIR"
cp "$BIN" "$OUT_DIR/DogForce Security Services.exe"
echo "==> Portable exe: $OUT_DIR/DogForce Security Services.exe"
echo "    (see $OUT_DIR/README.txt for the staff-facing run instructions)"
