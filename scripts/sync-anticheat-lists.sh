#!/bin/bash
set -euo pipefail

# Populates AzuAntiCheat Whitelist and Greylist folders with mod DLLs.
# Whitelist = required mods from manifest.json (players must have these)
# Greylist  = optional mods from greylist.json (players can connect with or without)
#
# Usage: ./scripts/sync-anticheat-lists.sh manifest.json [greylist.json]

PLUGINS_DIR="/home/valheim/server/BepInEx/plugins"
WHITELIST_DIR="/home/valheim/server/BepInEx/config/AzuAntiCheat_Whitelist"
GREYLIST_DIR="/home/valheim/server/BepInEx/config/AzuAntiCheat_Greylist"

# Note: we don't clear existing lists — manually-added DLLs
# (e.g. local mods like ValTicket) would be wiped. Instead we
# just copy/overwrite managed DLLs into the folders.

# --- Whitelist: copy DLLs for all mods in manifest.json ---
MANIFEST="${1:-manifest.json}"
if [ -f "$MANIFEST" ]; then
  echo "Building whitelist from $MANIFEST..."
  count=0
  while IFS= read -r dep; do
    version=$(echo "$dep" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+$')
    prefix="${dep%-"$version"}"
    namespace="${prefix%%-*}"
    name="${prefix#"$namespace"-}"

    # Skip BepInEx pack and libraries that aren't BepInEx plugins
    case "$name" in
      BepInExPack_Valheim) continue ;;
    esac

    mod_dir="$PLUGINS_DIR/$namespace-$name"
    if [ -d "$mod_dir" ]; then
      for dll in "$mod_dir"/*.dll; do
        [ -f "$dll" ] || continue
        cp "$dll" "$WHITELIST_DIR/"
        ((count++)) || true
      done
    fi
  done < <(jq -r '.dependencies[]' "$MANIFEST")
  echo "  Copied $count DLLs to whitelist"
else
  echo "Warning: $MANIFEST not found, skipping whitelist"
fi

# --- Greylist: copy DLLs for optional mods from greylist.json ---
GREYLIST_JSON="${2:-greylist.json}"
if [ -f "$GREYLIST_JSON" ]; then
  echo "Building greylist from $GREYLIST_JSON..."
  count=0
  while IFS= read -r dep; do
    version=$(echo "$dep" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+$')
    prefix="${dep%-"$version"}"
    namespace="${prefix%%-*}"
    name="${prefix#"$namespace"-}"

    mod_dir="$PLUGINS_DIR/$namespace-$name"
    if [ -d "$mod_dir" ]; then
      for dll in "$mod_dir"/*.dll; do
        [ -f "$dll" ] || continue
        cp "$dll" "$GREYLIST_DIR/"
        ((count++)) || true
      done
    fi
  done < <(jq -r '.dependencies[]' "$GREYLIST_JSON")
  echo "  Copied $count DLLs to greylist"
else
  echo "No greylist.json found, skipping greylist"
fi

# Fix ownership so the valheim user can read the DLLs at runtime.
# The github-runner user copies them, but AzuAntiCheat runs as valheim.
chown -R valheim:valheim "$WHITELIST_DIR" "$GREYLIST_DIR" 2>/dev/null || true
chmod -R 775 "$WHITELIST_DIR" "$GREYLIST_DIR" 2>/dev/null || true

echo ""
echo "Whitelist: $(ls "$WHITELIST_DIR"/*.dll 2>/dev/null | wc -l | tr -d ' ') DLLs"
echo "Greylist:  $(ls "$GREYLIST_DIR"/*.dll 2>/dev/null | wc -l | tr -d ' ') DLLs"
