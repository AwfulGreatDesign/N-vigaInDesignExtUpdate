#!/usr/bin/env bash
set -euo pipefail

NAVIGA_CLIENT="/Library/Application Support/Adobe/CEP/extensions/NavigaAd/client"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$SCRIPT_DIR/../naviga-originals/client"

echo "=== Naviga Auto — Install ==="

# 1. Verify source files exist
if [ ! -f "$NAVIGA_CLIENT/index.html" ]; then
  echo "ERROR: Cannot find $NAVIGA_CLIENT/index.html"
  echo "Is the NavigaAd extension installed?"
  exit 1
fi

# 2. Check if already patched
if grep -q "naviga-auto.js" "$NAVIGA_CLIENT/index.html"; then
  echo "INFO: index.html already contains naviga-auto.js tag — skipping patch."
else
  # 3. Back up original index.html (if backup doesn't already exist from Task 0)
  mkdir -p "$BACKUP_DIR"
  if [ ! -f "$BACKUP_DIR/index.html" ]; then
    cp "$NAVIGA_CLIENT/index.html" "$BACKUP_DIR/index.html"
    echo "Backed up index.html to $BACKUP_DIR/index.html"
  fi

  # 4. Inject script tag before </body>
  sed -i.tmp 's|</body>|    <script type="text/javascript" src="naviga-auto.js"></script>\n</body>|' \
      "$NAVIGA_CLIENT/index.html"
  rm -f "$NAVIGA_CLIENT/index.html.tmp"
  echo "Patched index.html — added naviga-auto.js script tag"
fi

# 5. Copy naviga-auto.js to the extension client folder
cp "$SCRIPT_DIR/naviga-auto.js" "$NAVIGA_CLIENT/naviga-auto.js"
echo "Copied naviga-auto.js to $NAVIGA_CLIENT/"

echo ""
echo "=== Install complete ==="
echo "Restart Adobe InDesign for changes to take effect."
