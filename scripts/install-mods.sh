#!/bin/bash
set -euo pipefail

# Install mods from one or more JSON files with a "dependencies" array.
# Usage: ./scripts/install-mods.sh manifest.json [server-mods.json ...]

if [ $# -eq 0 ]; then
  echo "Usage: $0 <manifest.json> [additional.json ...]"
  exit 1
fi

FAILED=0
TOTAL=0

for FILE in "$@"; do
  if [ ! -f "$FILE" ]; then
    echo "Warning: $FILE not found, skipping"
    continue
  fi

  echo "Reading dependencies from $FILE..."
  DEPS=$(jq -r '.dependencies[]' "$FILE")
  COUNT=$(echo "$DEPS" | wc -l | tr -d ' ')
  echo "Found $COUNT dependencies"
  echo ""

  i=0
  echo "$DEPS" | while read -r dep; do
    i=$((i + 1))
    echo "[$i/$COUNT] Installing $dep..."
    if ! tcli install valheim "$dep"; then
      echo "WARNING: Failed to install $dep"
      FAILED=$((FAILED + 1))
    fi
  done

  TOTAL=$((TOTAL + COUNT))
done

if [ "$FAILED" -gt 0 ]; then
  echo ""
  echo "ERROR: $FAILED dependencies failed to install"
  exit 1
fi

# Copy mods from tcli profile into the server's BepInEx plugins directory
TCLI_PROFILE="$HOME/.config/ThunderstoreCLI/Profiles/valheim/DefaultProfile/BepInEx/plugins"
BEPINEX_PLUGINS="/home/valheim/server/BepInEx/plugins"

if [ -d "$TCLI_PROFILE" ]; then
  echo ""
  echo "Syncing mods from tcli profile to $BEPINEX_PLUGINS..."
  rsync -rv "$TCLI_PROFILE/" "$BEPINEX_PLUGINS/"
  echo "Synced $(find "$TCLI_PROFILE" -name '*.dll' | wc -l | tr -d ' ') mod DLLs"
else
  echo "WARNING: tcli profile not found at $TCLI_PROFILE"
fi

echo ""
echo "All $TOTAL dependencies installed successfully"
