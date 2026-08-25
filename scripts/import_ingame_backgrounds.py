"""Replace map background sources with the real in-game card art.

The originals in `map_backgrounds/_source/` were scraped from the wiki: they are
inconsistent (13 different resolutions, several badly upscaled) and in places
show a different shot than the game itself uses. This pulls the actual textures
the client renders on the map card.

Where they come from
--------------------
DataTool (github.com/overtools/owlib) can dump every UI texture in one pass::

    DataTool.exe "D:\\Overwatch" dump-ui-textures ./ui-textures

That is far cheaper than `extract-maps` per map -- ~2 minutes for the whole game
versus multiple minutes and gigabytes of models for a single map -- and the
images it writes are byte-identical.

Each texture is named by its GUID, and maps are matched to a GUID two ways:

* Older maps: `DataTool list-maps --json` exposes an `Image` GUID per map.
* Newer maps: their map-header asset carries no image fields at all, so those
  GUIDs were identified by eye and are listed in `GUID_OVERRIDES` below.

Usage::

    python scripts/import_ingame_backgrounds.py <ui-texture-dump-dir>

Then run `process_map_backgrounds.py` to regenerate the four webp widths.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / "map_backgrounds" / "_source"
MAPS_JSON = ROOT / "maps.json"

# Maps whose GUID could not be read from the game data. Newer maps store no
# image reference in their map header, so these were matched visually against
# the texture dump. Keep the comment on each -- it is the only record of why a
# given GUID belongs to a given map.
GUID_OVERRIDES: dict[str, str] = {
    "Aatlis": "00000004 6C6B",  # confirmed via extract-maps: the only 4K texture in the map's own Textures/
    "Antarctic Peninsula": "00000004 7505",
    "Arena Victoriae": "00000005 B0AD",
    "Gogadoro": "00000006 1AEC",
    "Hanaoka": "00000004 5477",
    "Neon Junction": "00000007 69E7",
    "New Junk City": "00000004 2F1B",
    "Oasis": "00000000 A76B",
    "Place Lacroix": "00000005 4301",
    "Powder Keg Mine": "00000005 42EB",
    "Practice Range": "00000004 3CDA",  # has an Image GUID, but that texture is absent from the UI dump
    "Redwood Dam": "00000005 B0B1",
    "Runasapi": "00000004 6C6E",
    "Samoa": "00000004 5A71",
    "Thames District": "00000006 71F4",
    "Throne of Anubis": "00000004 FC73",
    "Wuxing University - Water College": "00000006 D0A1",
}

# Maps left on their wiki image. Mastery Course has no entry in the game files
# at all; the rest have an Image GUID whose texture the UI dump does not carry,
# so recovering them would mean a full `extract-maps` run per map.
KNOWN_UNRESOLVED = {
    "Mastery Course",
    "Temple of Anubis",
    "Workshop Chamber",
    "Workshop Green Screen",
}


def normalize_guid(guid: str) -> str:
    """Accept '4 6C6B', '000000046C6B' or '46C6B' -> '000000046C6B'."""
    return guid.replace(" ", "").upper().rjust(12, "0")


def load_map_images() -> dict[str, str]:
    """name -> GUID, from list-maps JSON plus the manual overrides."""
    resolved = {name: normalize_guid(g) for name, g in GUID_OVERRIDES.items()}
    return resolved


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(f"usage: {Path(sys.argv[0]).name} <ui-texture-dump-dir>")
    dump = Path(sys.argv[1])
    if not dump.is_dir():
        sys.exit(f"not a directory: {dump}")

    maps = json.loads(MAPS_JSON.read_text(encoding="utf-8"))
    if isinstance(maps, dict):
        maps = list(maps.values())

    guids = load_map_images()
    extra = Path(__file__).with_name("ingame_background_guids.json")
    if extra.exists():
        # GUIDs resolved automatically from `list-maps --json`, written by the
        # companion export step so this file stays readable.
        guids.update(
            {k: normalize_guid(v) for k, v in json.loads(extra.read_text("utf-8")).items()}
        )

    copied, skipped, missing = 0, [], []
    for m in maps:
        name, background = m["name"], m["background"]
        slug = Path(background).stem
        guid = guids.get(name)
        if guid is None:
            (skipped if name in KNOWN_UNRESOLVED else missing).append(name)
            continue
        src = dump / f"{guid}.png"
        if not src.is_file():
            missing.append(f"{name} (texture {guid} not in dump)")
            continue
        # Always .png: the source is lossless and process_map_backgrounds.py
        # does the webp conversion. Remove any other extension for this slug so
        # a stale wiki .jpg can't win the glob later.
        for old in SOURCE_DIR.glob(f"{slug}.*"):
            old.unlink()
        shutil.copy2(src, SOURCE_DIR / f"{slug}.png")
        copied += 1

    print(f"copied {copied} in-game backgrounds into {SOURCE_DIR}")
    if skipped:
        print(f"kept wiki image for {len(skipped)}: {', '.join(sorted(skipped))}")
    if missing:
        print(f"\nUNRESOLVED ({len(missing)}):")
        for m in sorted(missing):
            print(f"  - {m}")


if __name__ == "__main__":
    main()
