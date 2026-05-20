# ow-data

Shared reference data for the Overwatch tooling ecosystem. Single source of truth for hero metadata, map list, hero portraits, and perk icons. Published as an npm package (GitHub Packages) and a Python wheel (GitHub Releases), consumed by **OverwatchSpotter** and **OverwatchStatsMCP**.

## Critical rules

**Never commit or push without explicit user approval.** Wait for "commit" / "commit and push" from the user.

## Why this repo exists

Before ow-data, both consumers maintained near-identical copies of:

- Hero list (`heroes.txt` in MCP, `ALL_HEROES` constant in Spotter)
- `perks.json` (51 heroes × 4 perks — in `OverwatchSpotter/resources/models/perk_classifier/` and `OverwatchStatsMCP/src/static/`, with encoding drift on Lúcio/Torbjörn)
- `hero_portraits/*.png` (51 files in both projects)
- `perks/<hero>/<perk>.png` (204 files in both projects)
- Map list (`maps.txt` — MCP only, but Spotter has no validation layer)

Every time Blizzard adds a hero, map, or perk, both repos had to be updated separately. Consolidating into one versioned package means **one PR per game patch** and eliminates encoding/naming drift.

## Scope (what lives here / what does not)

**In scope:** cross-project reference data.

- `heroes.json` — hero metadata (name, slug, role, subrole, portrait path, perks, aliases)
- `maps.json` — map metadata (name, mode, aliases, background)
- `hero_portraits/*.png` — one per hero
- `perks/<hero_slug>/<perk_slug>.png` — one per perk (~204 files)
- `map_backgrounds/<width>/<map_slug>.webp` — map background, 4 width variants (1920/1280/640/320)

**Out of scope:**

- ONNX models (`ban_classifier`, `perk_classifier`, rank YOLO) — Spotter-only runtime artifacts, stay in `OverwatchSpotter/resources/models/`.
- Training data / ML pipeline — stays in `OverwatchSpotter/machine_learning/`.
- Game-event parsing, match schemas, anything logic-shaped — belongs in the consumers.

Rule of thumb: **if it's static data describing the game that both projects need, it goes here. Everything else stays in the consumer.**

## Consumers

| Consumer                 | Location on disk                               | Package          | Install path                       |
| ------------------------ | ---------------------------------------------- | ---------------- | ---------------------------------- |
| OverwatchSpotter         | `C:\Users\yegor\Projects\OverwatchSpotter`     | `@overlooker-dev/ow-data` (npm) | GitHub Packages            |
| OverwatchStatsMCP        | `C:\Users\yegor\Projects\OverwatchStatsMCP`    | `ow-data` (pip)  | Wheel attached to GitHub Release   |

Read their source freely to understand how they consume the data — they're right next door.

## Layout

```
ow-data/
├── CLAUDE.md
├── heroes.json                    # canonical hero metadata
├── maps.json                      # canonical map metadata
├── hero_portraits/*.png           # 51 files
├── perks/<hero_slug>/<perk_slug>.png  # ~204 files
├── map_backgrounds/                # map backgrounds (webp)
│   ├── 1920/ 1280/ 640/ 320/      #   62 files each — width variants
│   └── _source/                   #   original downloads, not published
├── package.json                   # npm package manifest
├── tsconfig.json
├── src/
│   └── index.ts                   # npm entry — exports types + helpers
├── pyproject.toml                 # python package manifest
├── ow_data/
│   ├── __init__.py                # python entry — exposes data + helpers
│   └── py.typed
└── .github/workflows/release.yml  # publishes both packages on tag push
```

## Data schemas

### `heroes.json`

Array of hero objects. One entry per playable hero. Order is not semantically meaningful but alphabetical by `name` is preferred for diffs.

```json
[
  {
    "name": "D.Va",
    "slug": "dva",
    "role": "tank",
    "subrole": "bruiser",
    "portrait": "hero_portraits/DVa.png",
    "color": "#F498BD",
    "aliases": ["DVa", "D Va", "DVA"],
    "perks": [
      { "name": "Groggy",  "slug": "groggy",  "tier": "minor", "slot": 1, "icon": "perks/dva/groggy.png" },
      { "name": "...",     "slug": "...",     "tier": "minor", "slot": 2, "icon": "perks/dva/...png" },
      { "name": "...",     "slug": "...",     "tier": "major", "slot": 3, "icon": "perks/dva/...png" },
      { "name": "...",     "slug": "...",     "tier": "major", "slot": 4, "icon": "perks/dva/...png" }
    ]
  }
]
```

When a perk is replaced mid-lifecycle, both the old and new entries live in the same `perks` array, sharing a slot with non-overlapping active windows:

```json
{ "name": "Divine Momentum", "slug": "divine_momentum", "tier": "minor", "slot": 2,
  "icon": "perks/mercy/divine_momentum.png", "removed_on": "2026-05-12" },
{ "name": "Winged Reach",    "slug": "winged_reach",    "tier": "minor", "slot": 2,
  "icon": "perks/mercy/winged_reach.png",    "added_on":   "2026-05-12" }
```

Field rules:

- `name` — canonical display name as shown in the game (e.g., `D.Va`, `Soldier: 76`, `Lúcio`). This is what users see.
- `slug` — lowercase, no punctuation, underscores for spaces (`dva`, `soldier_76`, `lucio`, `wrecking_ball`). Used in file paths and as a stable identifier.
- `role` — one of `tank` | `damage` | `support`.
- `subrole` — free-form but consistent. Current values in the source data: `specialist`, `flanker`, `tactician`, `medic`, `initiator`, `stalwart`, `recon`, `sharpshooter`, `survivor`, `bruiser`.
- `portrait` — repo-relative path to the PNG. File must exist.
- `color` — accent color as a `#RRGGBB` hex string. Curated per hero from the in-game/portrait palette. Used by client UIs that need a single hero-keyed color (e.g., hero-swap timelines, role bars).
- `aliases` — strings commonly produced by OCR, alternate spellings, and accent-stripped forms. Used by `normalize_hero_name()` before falling back to fuzzy matching. Do **not** include `name` itself — the lookup table handles that.
- `perks` — all perks the hero has *ever* had, including ones that have since been removed. At any given date, exactly 4 perks must be active (one per slot 1-4, slots 1-2 minor, slots 3-4 major). When a perk is removed and replaced, keep the old entry (set `removed_on`) and add the new entry (set `added_on`); both can share a slot as long as their active windows do not overlap. `slug` is unique within the hero (including historic perks — never reuse a slug).
- `icon` — repo-relative path to the perk PNG. File must exist. Historic perk icons stay in the package — consumers render them for old matches.
- `added_on` *(optional)* — ISO date (`YYYY-MM-DD`) the perk went live in-game. Absent = "has existed since we started tracking" (treat as the beginning of time).
- `removed_on` *(optional)* — ISO date the perk was removed in-game. Absent = currently active. A perk is active on date `d` iff `(added_on ?? -∞) ≤ d < (removed_on ?? +∞)`.

### `maps.json`

Array of map objects.

```json
[
  { "name": "King's Row",    "mode": "hybrid",  "aliases": ["Kings Row"], "background": "king_s_row.webp" },
  { "name": "Circuit Royal", "mode": "escort",  "aliases": [],            "background": "circuit_royal.webp" },
  { "name": "Paraíso",       "mode": "hybrid",  "aliases": ["Paraiso"],   "background": "paraiso.webp" }
]
```

Field rules:

- `name` — canonical map name as Blizzard spells it.
- `mode` — one of `control` | `escort` | `hybrid` | `push` | `flashpoint` | `clash` | `payload_race` | `assault` | `capture_the_flag` | `deathmatch` | `elimination` | `workshop` | `training`. Add new modes as they ship. The first six are Standard Play competitive modes; `payload_race` is Stadium-exclusive; `assault`/`capture_the_flag`/`deathmatch`/`elimination` are Arcade; `workshop` and `training` are custom games / training maps.
- `aliases` — accent-stripped or punctuation-stripped forms (e.g., `"Paraiso"`, `"Kings Row"`, `"Chateau Guillard"`), OCR variants, and common misspellings. Stadium maps that share a base theme with a Standard map are distinct maps with distinct names (e.g., Stadium's `Busan Sanctuary` vs Standard's `Busan`) — do **not** alias one to the other.
- `background` — background image filename (just the filename, e.g. `route_66.webp`). The same filename exists under every width directory in `map_backgrounds/`. Use `mapBackground()` / `map_background()` to build a width-specific repo-relative path — do not hardcode the path in consumer code.

## Asset conventions

- **Hero portraits:** `hero_portraits/<slug-or-filename>.png`. The current filename scheme in both consumers uses the hero's display-name with punctuation stripped (`DVa.png`, `Soldier_76.png`, `Wrecking_Ball.png`, `Jetpack_Cat.png`, `Junker_Queen.png`). Preserve that scheme so nothing in MCP's templates has to change. The `portrait` field in `heroes.json` is the source of truth for the exact filename — do not hardcode the transformation in consumer code.
- **Perk icons:** `perks/<hero_slug>/<perk_slug>.png`. Hero slug is the `slug` from `heroes.json`. Perk slug is the `slug` from the perk entry.
- **Map backgrounds:** `map_backgrounds/<width>/<map_slug>.webp`, where `<width>` is one of `1920`, `1280`, `640`, `320` and the filename is the `background` field from `maps.json`. The same filename exists under all four width directories (smaller-than-target sources are not upscaled, so a few low-res maps have an unchanged image in the larger directories). Originals live in `map_backgrounds/_source/` and are **not** published. Regenerate variants with `scripts/process_map_backgrounds.py`; re-fetch sources with `scripts/fetch_map_backgrounds.py`.

## npm package (`@overlooker-dev/ow-data`)

Published to GitHub Packages (`https://npm.pkg.github.com`).

### What it exports (`src/index.ts`)

```ts
export interface Perk {
  name: string;
  slug: string;
  tier: "minor" | "major";
  slot: 1 | 2 | 3 | 4;
  icon: string;        // repo-relative path; use assetPath() for absolute
  added_on?: string;   // ISO date; undefined = always-existed
  removed_on?: string; // ISO date; undefined = currently active
}

export interface Hero {
  name: string;
  slug: string;
  role: "tank" | "damage" | "support";
  subrole: string;
  portrait: string;
  color: string;        // #RRGGBB accent
  aliases: string[];
  perks: Perk[];
}

export interface GameMap {
  name: string;
  mode:
    | "control" | "escort" | "hybrid" | "push" | "flashpoint" | "clash"
    | "payload_race"
    | "assault" | "capture_the_flag" | "deathmatch" | "elimination"
    | "workshop" | "training";
  aliases: string[];
  background: string;   // webp filename; use mapBackground() for a width-specific path
}

export type MapBackgroundWidth = 1920 | 1280 | 640 | 320;

export const heroes: Hero[];
export const maps: GameMap[];

export const ALL_HERO_NAMES: string[];
export const ALL_MAP_NAMES: string[];
export const MAP_BACKGROUND_WIDTHS: readonly [1920, 1280, 640, 320];

export function getHero(nameOrAlias: string): Hero | undefined;
export function getMap(nameOrAlias: string): GameMap | undefined;
export function normalizeHeroName(input: string): string | undefined;  // exact + alias match
export function normalizeMapName(input: string): string | undefined;

/** Repo-relative path to a map's background at the given width; use assetPath() for absolute. */
export function mapBackground(map: GameMap, width: MapBackgroundWidth): string;

/** Perks active on the given ISO date (defaults to today). Always 4 entries. */
export function getActivePerks(hero: Hero, date?: string): Perk[];
/** Look up a perk by slug regardless of lifecycle (for historic matches). */
export function getPerk(hero: Hero, perkSlug: string): Perk | undefined;
/** True iff the perk was active on the given ISO date. */
export function isPerkActive(perk: Perk, date: string): boolean;

/** Returns absolute filesystem path to a packaged asset. */
export function assetPath(relativePath: string): string;
```

Fuzzy matching (edit-distance fallback) stays in the **consumer** — Spotter's `matchHeroName()` can call `normalizeHeroName()` first, then fall back to its existing fuzzy logic against `ALL_HERO_NAMES`. The package provides the data, not the fuzziness.

### Publishing

- `package.json` field: `"publishConfig": { "registry": "https://npm.pkg.github.com" }`
- `files` includes: `dist/`, `heroes.json`, `maps.json`, `hero_portraits/`, `perks/`, and the `map_backgrounds/` width directories (`_source/` excluded)
- GitHub Actions workflow on tag push builds and publishes.

### Consuming in Spotter

Add to `OverwatchSpotter/.npmrc`:

```
@overlooker-dev:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=${GITHUB_TOKEN}
```

Each dev/CI needs a PAT with `read:packages` scope.

`src/renderer/src/assets/hero-portraits.ts` switches from `import.meta.glob('resources/hero_portraits/*.png')` to globbing the package's `hero_portraits/` directory (Vite handles `node_modules` paths the same way). `src/renderer/src/assets/perks.ts` does the same for `perks.json` and `perks/`. `src/engine/util/heroes.ts` imports `ALL_HERO_NAMES` instead of hardcoding.

## Python package (`ow-data`)

GitHub Packages does not host PyPI, so we ship a wheel attached to a GitHub Release.

### What it exposes (`ow_data/__init__.py`)

```python
from ow_data import (
    heroes, maps,                           # parsed lists
    ALL_HERO_NAMES, ALL_MAP_NAMES,
    get_hero, get_map,
    normalize_hero_name, normalize_map_name,
    get_active_perks, get_perk, is_perk_active,  # perk lifecycle helpers
    map_background, MAP_BACKGROUND_WIDTHS,   # map background path helper
    asset_path,                             # pathlib.Path to packaged asset
    hero_portraits_dir, perks_dir,          # pathlib.Path for Starlette mounts
    map_backgrounds_dir,                    # pathlib.Path for Starlette mounts
)
```

Use `importlib.resources.files("ow_data")` internally so the module works both installed and in editable mode.

### Publishing

- `pyproject.toml` uses hatchling. Package data includes `heroes.json`, `maps.json`, `hero_portraits/**/*.png`, `perks/**/*.png`, `map_backgrounds/{1920,1280,640,320}/*.webp` (`_source/` excluded).
- Release workflow runs `python -m build`, attaches `ow_data-X.Y.Z-py3-none-any.whl` to the GitHub Release.

### Consuming in MCP

`pyproject.toml` dependency:

```toml
"ow-data @ https://github.com/overlooker-dev/ow-data/releases/download/v0.1.0/ow_data-0.1.0-py3-none-any.whl"
```

Changes in MCP:

- `src/main.py`: replace `VALID_HEROES` / `VALID_MAPS` loading and `normalize_hero_name` / `normalize_map_name` with imports from `ow_data`. Keep the `_HERO_LOOKUP` / `_MAP_LOOKUP` patterns if they're useful; otherwise use the package helpers directly.
- `src/public_match.py`: `_portraits_dir = ow_data.hero_portraits_dir`.
- `src/templates/scoreboard/match.html`: no change — still `/static/hero_portraits/...`, but the Starlette mount points at the package directory.
- Delete: `heroes.txt`, `maps.txt`, `src/static/perks.json`, `src/static/hero_portraits/`, `src/static/perks/`.

## Versioning

Semver. Bumps:

- **Patch** — new hero aliases, fixed typos, corrected perk names, re-exported portraits.
- **Minor** — new hero, new map, new perk, new field added to schema.
- **Major** — schema-breaking change (renamed field, changed shape, removed export).

One tag publishes both packages. Keep the npm and Python versions in lockstep.

## Migration tasks (for fresh session)

These are the things that need doing on top of the scaffold. Do them roughly in order; sub-bullets are checkpoints.

1. **Populate `heroes.json`.** Merge these sources:
   - `OverwatchStatsMCP/heroes.txt` (canonical name list, 51)
   - `OverwatchSpotter/resources/models/perk_classifier/perks.json` (role, subrole, per-hero perks, perk icons)
   - `OverwatchSpotter/resources/hero_portraits/*.png` (for portrait filenames)
   - `OverwatchStatsMCP/src/static/perks.json` (compare for encoding drift — pick the correct Unicode spellings of Lúcio, Torbjörn)
   - Derive `slug` from the portrait filename convention (`DVa` → `dva`, `Soldier_76` → `soldier_76`). Validate that every portrait has a hero entry and vice versa.
   - Seed `aliases` with accent-stripped forms (`Lucio`, `Torbjorn`) and obvious variants (`DVa` as alias of `D.Va`, `Kings Row` of `King's Row` — wait, that's a map).

2. **Populate `maps.json`.** Source: `OverwatchStatsMCP/maps.txt`. Decide the correct `mode` for each — this is new information, not currently stored. Stadium-exclusive maps (e.g., `Busan Sanctuary`, `Ilios Ruins`, `Arena Victoriae`) are distinct entries, not aliases of the Standard map they share a theme with. Arcade and custom/training maps are also in scope — see the `mode` enum in the schema.

3. **Copy assets.**
   - Copy `OverwatchSpotter/resources/hero_portraits/*.png` → `hero_portraits/`. Verify 51 files; diff against MCP's copy in case they drift.
   - Copy `OverwatchSpotter/resources/perks/<hero>/*.png` → `perks/<hero>/`. Verify counts match perks in `heroes.json`.

4. **Implement `src/index.ts`.** The skeleton has TODO markers. Bundle helpers, ship `.d.ts` via `tsc --declaration`.

5. **Implement `ow_data/__init__.py`.** Mirror the TS API. Use `importlib.resources.files()` for asset paths.

6. **Implement `.github/workflows/release.yml`.** On tag push (`v*`):
   - Build TS → `dist/`, run `npm publish` against GitHub Packages.
   - Run `python -m build`, create GitHub Release, attach wheel.
   - Gate both on passing a validation check (see task 7).

7. **Add a validation script.** `scripts/validate.ts` (or `.py`) that asserts:
   - Every hero's `portrait` path exists on disk.
   - Every perk's `icon` path exists on disk.
   - Every portrait/perk file on disk is referenced by `heroes.json`.
   - Every hero has exactly 4 perks (2 minor slot 1-2, 2 major slot 3-4).
   - No duplicate slugs across heroes or perks-within-hero.
   - No alias collides with another hero's name or alias.
   - Every map's mode is in the allowed enum.
   Wire into CI so a bad edit fails loudly.

8. **Migrate OverwatchSpotter.**
   - Add `.npmrc` (gitignored) and CI secret.
   - `npm install @overlooker-dev/ow-data`.
   - Rewrite `src/engine/util/heroes.ts`, `src/renderer/src/assets/hero-portraits.ts`, `src/renderer/src/assets/perks.ts`, `src/engine/analysis/perk-detection.ts` to import from the package.
   - Delete `resources/hero_portraits/`, `resources/perks/`, `resources/models/perk_classifier/perks.json`, `resources/models/ban_classifier/hero_names.txt` (keep the ONNX).
   - Update `electron-builder.yml` `asarUnpack` if Vite no longer inlines the assets (likely does; verify).
   - Test: run `npm run dev`, verify portraits + perk icons render in Dashboard.

9. **Migrate OverwatchStatsMCP.**
   - Add `ow-data` wheel dependency.
   - Rewrite `src/main.py` hero/map validation to use `ow_data`.
   - Point `src/public_match.py` `_portraits_dir` at the package.
   - Delete `heroes.txt`, `maps.txt`, `src/static/perks.json`, `src/static/hero_portraits/`, `src/static/perks/`.
   - Update Starlette static mount if needed.
   - Test: run the public match template for a real match; verify portraits + perks load.

10. **Cut `v0.1.0`.** Tag, let the workflow publish, pin both consumers.

## Gotchas

- **Encoding drift.** The two existing `perks.json` copies disagree on Lúcio/Torbjörn. The canonical source is *your eyes* — verify against the game, not either existing file.
- **Jetpack Cat / Freja / Mizuki / Wuyang / Venture / Hazard / Juno / Illari / Mauga / Ramattra / Kiriko / Lifeweaver / Sombra / Sigma / Brigitte / Ashe / Sojourn / Domina / Emre / Vendetta / Anran / Sierra etc.** — the 51-hero list already includes all of these in the existing files. Use it as-is; don't drop heroes you don't recognize.
- **"Domina", "Emre", "Vendetta", "Anran", "Sierra", "Mizuki", "Wuyang"** — some of these are newer or less familiar. Don't manually curate them out; preserve whatever the source files have unless you can verify a hero was actually removed.
- **No LFS needed.** Without ONNX models, the package is small enough (~few MB of PNGs) that plain git handles it fine. Keeps `npm publish` and `python -m build` simple — no `git lfs pull` step required in CI.
- **PAT scope.** Both consumers need a GitHub PAT with `read:packages` (for npm) in CI. Dev machines need the same in their global `~/.npmrc`. Document this in each consumer's README when migrating.
- **Map mode metadata is new.** It doesn't exist in the current `maps.txt` — you're adding it. Don't guess; verify the mode of each map against the game or a wiki.

## Related projects

- `OverwatchSpotter` — the main companion app (Electron + React + TS).
- `OverwatchStatsMCP` — Python FastMCP server + PostgreSQL + public match scoreboard.
- `OverwatchLooker` — Python tray-app predecessor. No longer consumes this package (being superseded).
