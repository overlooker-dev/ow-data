# ow-data

Shared reference data for the **Overwatch** tooling ecosystem — the single source of truth for hero metadata, the map list, hero portraits/icons, perk icons, and map backgrounds.

It ships as two packages built from the same data:

- **npm** — `@overlooker-dev/ow-data` (GitHub Packages), for TypeScript/JavaScript consumers
- **Python** — `ow-data` wheel (attached to GitHub Releases), for Python consumers

One PR per game patch updates the data once; every consumer picks it up on the next version bump. No more maintaining parallel hero lists, `perks.json` copies, or duplicated portrait/perk PNGs across projects.

---

## What's inside

| Data | File |
| --- | --- |
| Hero metadata — name, slug, role, subrole, accent color, aliases, perks (with lifecycle dates) | `heroes.json` |
| Map metadata — name, mode, aliases, background | `maps.json` |
| Hero portraits — one per hero | `hero_portraits/*.png` |
| Hero select icons — one per hero | `hero_icons/*.png` |
| Perk icons — one per perk, including historic perks | `perks/<hero_slug>/<perk_slug>.png` |
| Map backgrounds — 4 width variants (1920/1280/640/320) | `map_backgrounds/<width>/<map_slug>.webp` |

The data describes **what the game contains** — it deliberately holds no game logic, match schemas, or ML models. Those stay in the consumers.

---

## Install & use

### TypeScript / JavaScript (npm)

The package is published to GitHub Packages. Add to your project's `.npmrc` (and provide a GitHub PAT with `read:packages`):

```
@overlooker-dev:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=${GITHUB_TOKEN}
```

```sh
npm install @overlooker-dev/ow-data
```

```ts
import {
  heroes, maps, ALL_HERO_NAMES,
  getHero, getMap, normalizeHeroName,
  getActivePerks, mapBackground,
} from "@overlooker-dev/ow-data";

getHero("Lucio")?.name;                 // "Lúcio"  (alias-aware)
normalizeHeroName("dva");               // "D.Va"
getActivePerks(getHero("Mercy")!);      // 4 perks active today
mapBackground(getMap("King's Row")!, 1280);
// -> "map_backgrounds/1280/king_s_row.webp"
```

Asset paths in the data are **repo-relative**. To resolve an absolute filesystem path in Node, use the `/node` subpath export:

```ts
import { assetPath } from "@overlooker-dev/ow-data/node";
assetPath(getHero("D.Va")!.portrait);   // absolute path to DVa.png
```

> The `/node` helper pulls in `node:path`/`node:url` — don't import it from a browser/renderer bundle. Bundlers (Vite, etc.) can glob the package's `hero_portraits/`, `perks/`, and `map_backgrounds/` directories directly.

### Python (wheel)

There's no PyPI host for this; the wheel is attached to each GitHub Release. Pin it in `pyproject.toml`:

```toml
"ow-data @ https://github.com/overlooker-dev/ow-data/releases/download/v0.7.0/ow_data-0.7.0-py3-none-any.whl"
```

```python
from ow_data import (
    heroes, maps, ALL_HERO_NAMES,
    get_hero, get_map, normalize_hero_name,
    get_active_perks, map_background, asset_path,
    hero_portraits_dir, hero_icons_dir, perks_dir, map_backgrounds_dir,
)

get_hero("Lucio").name                      # "Lúcio"
normalize_hero_name("dva")                   # "D.Va"
get_active_perks(get_hero("Mercy"))          # tuple of 4 active perks
asset_path(map_background(get_map("Ilios"), 640))   # pathlib.Path, absolute
```

`hero_portraits_dir` and friends are `pathlib.Path` objects pointing at the installed package data — convenient for Starlette/FastAPI static mounts.

Both APIs provide **exact + alias** lookups only. Fuzzy matching (edit-distance fallback) stays in the consumers, run against `ALL_HERO_NAMES` / `ALL_MAP_NAMES`.

---

## Data schemas

### `heroes.json`

```jsonc
{
  "name": "D.Va",                 // canonical display name, exactly as in-game
  "slug": "dva",                  // lowercase, underscores; stable identifier & path segment
  "role": "tank",                 // tank | damage | support
  "subrole": "initiator",         // free-form but consistent (bruiser, flanker, medic, ...)
  "portrait": "hero_portraits/DVa.png",
  "icon": "hero_icons/DVa.png",
  "color": "#F498BD",             // #RRGGBB accent, for hero-keyed UI
  "aliases": ["DVa", "D Va"],     // OCR/spelling variants; never includes `name` itself
  "perks": [
    { "name": "Bunny Power", "slug": "bunny_power", "tier": "minor", "slot": 1, "icon": "perks/dva/bunny_power.png" }
    // ...exactly 4 perks active on any date: slots 1–2 minor, slots 3–4 major
  ]
}
```

**Perk lifecycle.** Every perk a hero has *ever* had stays in the array, including removed ones — consumers render them for historic matches. When a perk is replaced, the old entry gets `removed_on` and the new one gets `added_on` (ISO `YYYY-MM-DD`); both share a slot with non-overlapping active windows. A perk is active on date `d` iff `(added_on ?? -∞) ≤ d < (removed_on ?? +∞)`. Slugs are unique within a hero and never reused.

### `maps.json`

```jsonc
{
  "name": "King's Row",
  "mode": "hybrid",               // control | escort | hybrid | push | flashpoint | clash
                                  // | payload_race | assault | capture_the_flag
                                  // | deathmatch | elimination | workshop | training
  "aliases": ["Kings Row"],       // accent-/punctuation-stripped & OCR variants
  "background": "king_s_row.webp" // filename only; same name exists under every width dir
}
```

Build width-specific background paths with `mapBackground()` / `map_background()` — don't hardcode them.

---

## Repo layout

```
ow-data/
├── heroes.json                       # canonical hero metadata
├── maps.json                         # canonical map metadata
├── hero_portraits/*.png
├── hero_icons/*.png
├── perks/<hero_slug>/<perk_slug>.png
├── map_backgrounds/
│   ├── 1920/ 1280/ 640/ 320/         # published width variants
│   └── _source/                      # original downloads (not published)
├── src/index.ts, src/node.ts         # npm entry (+ Node-only helpers)
├── ow_data/__init__.py               # python entry
├── scripts/                          # validate.ts + asset build/fetch helpers
└── .github/workflows/release.yml     # publishes both packages on tag push
```

---

## Updating for a game patch

1. Edit `heroes.json` / `maps.json` for the new heroes, maps, perks, or perk lifecycle changes.
2. Add any new asset files (`perks/<hero>/<perk>.png`, portraits, icons). For map backgrounds, drop a source image named `<map_slug>.<ext>` into `map_backgrounds/` and run `python scripts/process_map_backgrounds.py` to generate all four widths.
3. Run validation — it must pass before publishing:
   ```sh
   npm run validate
   ```
   It checks: every referenced asset exists, no orphan files on disk, exactly one perk active per slot today, valid roles/modes, no duplicate or colliding slugs/names/aliases, and well-formed lifecycle dates.
4. Bump the version in **both** `package.json` and `pyproject.toml` (keep them in lockstep).
5. Commit, then tag `vX.Y.Z` and push the tag — the release workflow builds and publishes both packages.

### Versioning (semver)

- **Patch** — new aliases, typo/perk-name fixes, re-exported assets.
- **Minor** — new hero, map, perk, or schema field.
- **Major** — schema-breaking change (renamed/removed field, changed shape).

One tag publishes both packages; npm and Python versions stay in lockstep.

---

## License

UNLICENSED — © overlooker-dev. The repository is public for reference and to support the consuming projects; it is not licensed for redistribution. Overwatch and all associated hero/map names and imagery are trademarks of Blizzard Entertainment; asset files are property of Blizzard and included here solely for use by the Overlooker tooling.
