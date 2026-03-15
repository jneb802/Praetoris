#!/bin/bash
set -euo pipefail

# Install mods from one or more JSON files with a "dependencies" array.
# Downloads directly from the Thunderstore API and extracts DLLs into BepInEx/plugins.
# Usage: ./scripts/install-mods.sh manifest.json [server-mods.json ...]

PLUGINS_DIR="/home/valheim/server/BepInEx/plugins"
PATCHERS_DIR="/home/valheim/server/BepInEx/patchers"

if [ $# -eq 0 ]; then
  echo "Usage: $0 <manifest.json> [additional.json ...]"
  exit 1
fi

tmp_dir=$(mktemp -d)
trap "rm -rf '$tmp_dir'" EXIT

failed=0
installed=0
skipped=0

for json_file in "$@"; do
  [ -f "$json_file" ] || { echo "Warning: $json_file not found, skipping"; continue; }

  echo "Reading dependencies from $json_file..."
  deps=$(jq -r '.dependencies[]' "$json_file")
  count=$(echo "$deps" | wc -l | tr -d ' ')
  echo "Found $count dependencies"
  echo ""

  i=0
  while IFS= read -r dep; do
    i=$((i + 1))

    # Parse namespace-name-version
    version=$(echo "$dep" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+$')
    prefix="${dep%-"$version"}"
    namespace="${prefix%%-*}"
    name="${prefix#"$namespace"-}"

    # BepInEx pack is managed by the server image
    if [[ "$name" == "BepInExPack_Valheim" ]]; then
      echo "[$i/$count] Skipping $namespace-$name (managed by server)"
      ((skipped++)) || true
      continue
    fi

    mod_dir="$PLUGINS_DIR/$namespace-$name"

    # Skip if already at this version
    if [ -f "$mod_dir/.version" ] && [ "$(cat "$mod_dir/.version")" = "$version" ]; then
      echo "[$i/$count] $namespace-$name@$version (up to date)"
      ((skipped++)) || true
      continue
    fi

    echo "[$i/$count] Installing $namespace-$name@$version..."

    url="https://thunderstore.io/package/download/$namespace/$name/$version/"
    zip_file="$tmp_dir/${namespace}-${name}.zip"
    extract_dir="$tmp_dir/${namespace}-${name}"

    if ! curl -sL -o "$zip_file" "$url"; then
      echo "  ERROR: Failed to download"
      ((failed++)) || true
      continue
    fi

    rm -rf "$extract_dir"
    mkdir -p "$extract_dir"
    if ! unzip -qo "$zip_file" -d "$extract_dir"; then
      echo "  ERROR: Failed to extract"
      ((failed++)) || true
      continue
    fi

    rm -rf "$mod_dir"
    mkdir -p "$mod_dir"

    # Copy plugin files (from plugins/ subdir and root)
    if [ -d "$extract_dir/plugins" ]; then
      cp -r "$extract_dir/plugins/"* "$mod_dir/" 2>/dev/null || true
    fi
    # Copy root-level DLLs and asset bundle manifests
    find "$extract_dir" -maxdepth 1 -name "*.dll" -exec cp {} "$mod_dir/" \;
    find "$extract_dir" -maxdepth 1 -name "assetBundleManifest*" -exec cp {} "$mod_dir/" \;

    # Copy patchers if present
    if [ -d "$extract_dir/patchers" ]; then
      mkdir -p "$PATCHERS_DIR"
      cp -r "$extract_dir/patchers/"* "$PATCHERS_DIR/" 2>/dev/null || true
    fi

    echo "$version" > "$mod_dir/.version"
    ((installed++)) || true

  done <<< "$deps"
done

echo ""
echo "Done: $installed installed, $skipped up-to-date, $failed failed"

if [ "$failed" -gt 0 ]; then
  echo "ERROR: $failed dependencies failed to install"
  exit 1
fi
