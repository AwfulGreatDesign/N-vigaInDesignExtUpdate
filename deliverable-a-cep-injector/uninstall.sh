#!/usr/bin/env bash
set -euo pipefail

NAVIGA_CLIENT="/Library/Application Support/Adobe/CEP/extensions/NavigaAd/client"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$SCRIPT_DIR/../naviga-originals/client"

echo "=== Naviga Auto — Uninstall ==="

# 1. Restore original index.html from backup
if [ -f "$BACKUP_DIR/index.html" ]; then
  cp "$BACKUP_DIR/index.html" "$NAVIGA_CLIENT/index.html"
  echo "Restored original index.html from backup"
else
  echo "WARNING: No backup found at $BACKUP_DIR/index.html"
  echo "Attempting to remove script tag manually..."
  sed -i.tmp '/<script type="text\/javascript" src="naviga-auto.js"><\/script>/d' \
      "$NAVIGA_CLIENT/index.html"
  rm -f "$NAVIGA_CLIENT/index.html.tmp"
  echo "Removed naviga-auto.js script tag from index.html"
fi

# 2. Remove naviga-auto.js from extension folder
if [ -f "$NAVIGA_CLIENT/naviga-auto.js" ]; then
  rm "$NAVIGA_CLIENT/naviga-auto.js"
  echo "Removed naviga-auto.js from $NAVIGA_CLIENT/"
fi

echo ""
echo "=== Uninstall complete ==="
echo "Restart Adobe InDesign to restore original behavior."
