# Praetoris

Hardcore exploration modpack for the Praetoris Valheim dedicated server — Season 5.

**Thunderstore:** https://thunderstore.io/c/valheim/p/warpalicious/Praetoris/
**Discord:** https://discord.gg/R9rb5REgD3

## Install

Install via [Thunderstore Mod Manager](https://www.overwolf.com/app/Thunderstore-Thunderstore_Mod_Manager) or [r2modman](https://thunderstore.io/package/ebkr/r2modman/) — search for "Praetoris" by warpalicious.

## Structure

```
manifest.json   # Package metadata + dependency list
icon.png        # 256x256 Thunderstore icon
README.md       # This file (displayed on Thunderstore)
CHANGELOG.md    # Version history
Config/         # BepInEx config files shipped to players
```

## Versioning

Format: `<season>.<major>.<patch>` — e.g. `5.0.0` = season 5 launch. `5.1.0` = first major update of season 5.

`main` always reflects what is live on the server. All changes go through work branches and PRs. Each release is tagged (e.g. `v5.0.0`).

```
git tag                              # list all releases
git tag -l "v5.*"                    # all season 5 releases
git diff v1.1.15..v5.0.0            # see what changed between seasons
git log v5.0.0..v5.1.0 --oneline    # changes within season 5
```

## Publishing

```bash
# Build zip from repo root
zip -r Praetoris-<version>.zip manifest.json icon.png README.md CHANGELOG.md Config/

# Publish
tcli publish \
  --file Praetoris-<version>.zip \
  --token <TOKEN> \
  --repository https://thunderstore.io \
  --package-namespace warpalicious \
  --package-name Praetoris \
  --package-version <version>
```
