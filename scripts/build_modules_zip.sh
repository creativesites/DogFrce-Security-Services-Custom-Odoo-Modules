#!/bin/bash
# Packages all security_* modules into a single dogforce_modules.zip for remote deployment.
# The zip contains each module directory at the top level so Odoo recognises them on extraction.
#
# Usage:
#   bash scripts/build_modules_zip.sh
#   bash scripts/build_modules_zip.sh --output /tmp/my_release.zip

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ADDONS_DIR="$PROJECT_ROOT/custom_addons"
OUTPUT="$PROJECT_ROOT/dogforce_modules.zip"

# Allow --output override
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output|-o)
            OUTPUT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Collect module directories (anything with a __manifest__.py)
modules=()
while IFS= read -r manifest; do
    modules+=("$(basename "$(dirname "$manifest")")")
done < <(find "$ADDONS_DIR" -maxdepth 2 -name "__manifest__.py" | sort)

if [ ${#modules[@]} -eq 0 ]; then
    echo "No Odoo modules found under $ADDONS_DIR"
    exit 1
fi

rm -f "$OUTPUT"

echo "Building $(basename "$OUTPUT") from ${#modules[@]} modules..."
echo ""

for mod_name in "${modules[@]}"; do
    (
        cd "$ADDONS_DIR"
        zip -rq "$OUTPUT" "$mod_name/" \
            --exclude "*/__pycache__/*" \
            --exclude "*/*.pyc" \
            --exclude "*/.DS_Store" \
            --exclude "*/*.zip"
    )
    echo "  + $mod_name"
done

SIZE=$(du -h "$OUTPUT" | cut -f1)
echo ""
echo "Done: $OUTPUT ($SIZE)"
echo ""
echo "Next steps:"
echo "  Deploy:  bash scripts/deploy_modules.sh --host user@your-server"
echo "  Or copy: scp $OUTPUT user@your-server:/tmp/"
