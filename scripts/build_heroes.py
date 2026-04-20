"""One-shot: generate heroes.json from Spotter's perks.json.

Reads: ../../OverwatchSpotter/resources/models/perk_classifier/perks.json
Writes: ../heroes.json

Transforms:
- Strips image_url, renames image_path -> icon, hyphens -> underscores.
- Derives perk slug from perk name (lowercase, punctuation stripped, spaces -> underscores).
- Derives portrait path from the display name using the existing filename convention
  (accent-strip, punctuation-strip, spaces -> underscores).
- Seeds aliases for accented / punctuated names.
- Sorts heroes alphabetically by name.
- Validates every portrait and perk icon exists on disk.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SPOTTER_PERKS = REPO.parent / "OverwatchSpotter" / "resources" / "models" / "perk_classifier" / "perks.json"
OUT = REPO / "heroes.json"


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def portrait_filename(name: str) -> str:
    """Match the existing filename scheme: accent-strip, punctuation-strip, spaces -> underscores."""
    s = strip_accents(name)
    s = re.sub(r"[^\w\s]", "", s)  # strip punctuation (keeps letters/digits/underscores)
    s = re.sub(r"\s+", "_", s.strip())
    return f"{s}.png"


def perk_slug(name: str) -> str:
    """Mirrors on-disk convention: any run of non-alphanumeric collapses to one underscore."""
    s = strip_accents(name).lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


ALIAS_MAP: dict[str, list[str]] = {
    "D.Va": ["DVa", "D Va"],
    "Soldier: 76": ["Soldier 76", "Soldier_76", "Soldier76", "Soldier-76"],
    "Lúcio": ["Lucio"],
    "Torbjörn": ["Torbjorn"],
    "Wrecking Ball": ["Wrecking_Ball", "WreckingBall"],
    "Junker Queen": ["Junker_Queen", "JunkerQueen"],
    "Jetpack Cat": ["Jetpack_Cat", "JetpackCat"],
}


def aliases_for(name: str) -> list[str]:
    return ALIAS_MAP.get(name, [])


def main() -> int:
    raw = json.loads(SPOTTER_PERKS.read_text(encoding="utf-8"))
    src_heroes = raw["heroes"]

    out_heroes = []
    errors: list[str] = []

    for h in src_heroes:
        name = h["name"]
        slug = h["slug"].replace("-", "_")
        portrait_rel = f"hero_portraits/{portrait_filename(name)}"

        perks_out = []
        for p in h["perks"]:
            pname = p["name"]
            pslug = perk_slug(pname)
            icon_rel = f"perks/{slug}/{pslug}.png"
            perks_out.append({
                "name": pname,
                "slug": pslug,
                "tier": p["tier"],
                "slot": p["slot"],
                "icon": icon_rel,
            })
            if not (REPO / icon_rel).exists():
                errors.append(f"missing perk icon: {icon_rel} (hero {slug}, perk {pname!r})")

        if not (REPO / portrait_rel).exists():
            errors.append(f"missing portrait: {portrait_rel} (hero {name!r})")

        out_heroes.append({
            "name": name,
            "slug": slug,
            "role": h["role"],
            "subrole": h["subrole"],
            "portrait": portrait_rel,
            "aliases": aliases_for(name),
            "perks": perks_out,
        })

    out_heroes.sort(key=lambda h: strip_accents(h["name"]).lower())

    if errors:
        print("VALIDATION ERRORS:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    OUT.write_text(json.dumps(out_heroes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(out_heroes)} heroes to {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
