#!/usr/bin/env bash
# Builds the Windows NSIS installer from macOS (cargo-xwin), signed for the
# in-app updater, plus the latest.json manifest the updater reads.
#
# Fallback for when the normal path (GitHub Actions Windows runner,
# .github/workflows/desktop-build.yml) isn't available. Produces NSIS only:
# MSI needs WiX, which only runs on Windows. The NSIS installer is also what
# the updater downloads, so nothing is lost for updates.
#
# This is *update* signing (Tauri's minisign key, so installed apps accept
# the update). It is NOT Windows code signing -- SmartScreen will still
# warn on first install until a code-signing certificate exists
# (BUILD-STATUS-AND-PHASE-PLAN.md 1.2/1.3).
#
# One-time setup:
#   rustup target add x86_64-pc-windows-msvc
#   cargo install --locked cargo-xwin
#   brew install llvm nsis   # llvm: ring/rustls need llvm-lib to cross-link
#                            # for MSVC (rustup's llvm-tools doesn't ship it);
#                            # nsis: makensis builds the installer.
#   Updater key: ~/.tauri/dogforce-updater.key, its password in the macOS
#   Keychain under service "dogforce-desktop-updater-key". BACK BOTH UP --
#   if this key is lost, installed copies can never auto-update again and
#   every machine needs a manual reinstall.
#
# Usage:
#   bash scripts/build-windows-xcompile.sh ["release notes shown to users"]
#
# Production only. DogForce's staging Odoo only listens on localhost:8070 on
# the production host, so there's no staging URL a desktop app elsewhere
# could reach. Override DEPLOYGUARD_ODOO_BASE_URL/_DB to point elsewhere.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT_DIR="$DESKTOP_DIR/dist-windows"
RELEASES_REPO="creativesites/dogforce-desktop-releases"
NOTES="${1:-Bug fixes and improvements.}"

export DEPLOYGUARD_ODOO_BASE_URL="${DEPLOYGUARD_ODOO_BASE_URL:-https://dogforcesecurityservices.com}"
export DEPLOYGUARD_ODOO_DB="${DEPLOYGUARD_ODOO_DB:-dogforce_prod}"

KEY_FILE="$HOME/.tauri/dogforce-updater.key"
if [ ! -f "$KEY_FILE" ]; then
  echo "error: updater key not found at $KEY_FILE"
  exit 1
fi
export TAURI_SIGNING_PRIVATE_KEY="$(cat "$KEY_FILE")"
TAURI_SIGNING_PRIVATE_KEY_PASSWORD="$(security find-generic-password -s dogforce-desktop-updater-key -w)" || {
  echo "error: updater key password not found in Keychain (service dogforce-desktop-updater-key)"
  exit 1
}
export TAURI_SIGNING_PRIVATE_KEY_PASSWORD

if ! command -v llvm-lib >/dev/null 2>&1; then
  export PATH="/opt/homebrew/opt/llvm/bin:$PATH"
fi
for tool in llvm-lib makensis; do
  command -v "$tool" >/dev/null 2>&1 || { echo "error: $tool not found. Run: brew install llvm nsis"; exit 1; }
done

cd "$DESKTOP_DIR"
VERSION="$(node -p "require('./src-tauri/tauri.conf.json').version")"
echo "==> Building v$VERSION against $DEPLOYGUARD_ODOO_BASE_URL"

npx tauri build --target x86_64-pc-windows-msvc --runner cargo-xwin --bundles nsis

NSIS_DIR="$DESKTOP_DIR/src-tauri/target/x86_64-pc-windows-msvc/release/bundle/nsis"
INSTALLER="$(ls "$NSIS_DIR"/*_"$VERSION"_x64-setup.exe 2>/dev/null | head -1)"
if [ -z "$INSTALLER" ] || [ ! -f "$INSTALLER.sig" ]; then
  echo "error: expected an installer and its .sig in $NSIS_DIR"
  exit 1
fi

# GitHub rewrites spaces in asset names, so ship a space-free name and make
# latest.json point at exactly that. The .sig covers the file's bytes, not
# its name, so renaming doesn't invalidate it.
ASSET="DogForce-Security-Services_${VERSION}_x64-setup.exe"
mkdir -p "$OUT_DIR"
cp "$INSTALLER" "$OUT_DIR/$ASSET"
cp "$INSTALLER.sig" "$OUT_DIR/$ASSET.sig"

node - "$VERSION" "$NOTES" "$OUT_DIR/$ASSET.sig" "https://github.com/$RELEASES_REPO/releases/download/v$VERSION/$ASSET" "$OUT_DIR/latest.json" <<'EOF'
const fs = require("fs");
const [version, notes, sigPath, url, outPath] = process.argv.slice(2);
const manifest = {
  version,
  notes,
  pub_date: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
  platforms: {
    "windows-x86_64": { signature: fs.readFileSync(sigPath, "utf8").trim(), url },
  },
};
fs.writeFileSync(outPath, JSON.stringify(manifest, null, 2) + "\n");
EOF

echo "==> Installer:  $OUT_DIR/$ASSET"
echo "==> Signature:  $OUT_DIR/$ASSET.sig"
echo "==> Manifest:   $OUT_DIR/latest.json"
echo
echo "To publish (installed apps pick it up within 6 hours, or on next launch):"
echo "  gh release create v$VERSION --repo $RELEASES_REPO --title \"DogForce Desktop $VERSION\" \\"
echo "    --notes \"$NOTES\" \"$OUT_DIR/$ASSET\" \"$OUT_DIR/latest.json\""
