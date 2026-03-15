#!/bin/bash
set -euo pipefail

# Install all mods from manifest.json dependencies via tcli
# Usage: ./scripts/install-mods.sh [manifest.json path]

MANIFEST="${1:-manifest.json}"

if [ ! -f "$MANIFEST" ]; then
  echo "Error: $MANIFEST not found"
  exit 1
fi

echo "Reading dependencies from $MANIFEST..."
DEPS=$(jq -r '.dependencies[]' "$MANIFEST")
COUNT=$(echo "$DEPS" | wc -l)
echo "Found $COUNT dependencies"
echo ""

FAILED=0
i=0
echo "$DEPS" | while read -r dep; do
  i=$((i + 1))
  echo "[$i/$COUNT] Installing $dep..."
  if ! tcli install valheim "$dep"; then
    echo "WARNING: Failed to install $dep"
    FAILED=$((FAILED + 1))
  fi
done

if [ "$FAILED" -gt 0 ]; then
  echo ""
  echo "ERROR: $FAILED dependencies failed to install"
  exit 1
fi

echo ""
echo "All $COUNT dependencies installed successfully"
