# Praetoris

Hardcore exploration modpack for the Praetoris Valheim dedicated server.

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

Each release is a git tag (e.g. `v1.1.15`). `main` always reflects what is currently live on the server.

- `git tag` — list all releases
- `git diff v1.1.15..v1.2.0` — see what changed between versions
- `git checkout v1.1.15` — view the exact state of a past release

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
