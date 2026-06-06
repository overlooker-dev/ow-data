"""ow-data — shared reference data for OverwatchSpotter and OverwatchStatsMCP.

Exposes hero metadata, map list, and asset paths. Fuzzy matching stays in the
consumers; this module provides exact + alias lookups only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date as _date
from importlib.resources import files
from pathlib import Path
from typing import Literal

__all__ = [
    "Hero",
    "Perk",
    "GameMap",
    "heroes",
    "maps",
    "ALL_HERO_NAMES",
    "ALL_MAP_NAMES",
    "get_hero",
    "get_map",
    "normalize_hero_name",
    "normalize_map_name",
    "get_active_perks",
    "get_perk",
    "is_perk_active",
    "map_background",
    "MAP_BACKGROUND_WIDTHS",
    "asset_path",
    "hero_portraits_dir",
    "hero_icons_dir",
    "perks_dir",
    "map_backgrounds_dir",
]

Role = Literal["tank", "damage", "support"]
PerkTier = Literal["minor", "major"]
MapMode = Literal[
    "control",
    "escort",
    "hybrid",
    "push",
    "flashpoint",
    "clash",
    "payload_race",
    "assault",
    "capture_the_flag",
    "deathmatch",
    "elimination",
    "workshop",
    "training",
]


@dataclass(frozen=True, slots=True)
class Perk:
    name: str
    slug: str
    tier: PerkTier
    slot: int  # 1-4
    icon: str  # package-relative path
    added_on: str | None = None  # ISO date the perk went live; None = always-existed
    removed_on: str | None = None  # ISO date the perk was removed; None = currently active


@dataclass(frozen=True, slots=True)
class Hero:
    name: str
    slug: str
    role: Role
    subrole: str
    portrait: str
    icon: str  # repo-relative path to the hero's square icon PNG
    color: str  # accent color as #RRGGBB
    aliases: tuple[str, ...]
    perks: tuple[Perk, ...]


@dataclass(frozen=True, slots=True)
class GameMap:
    name: str
    mode: MapMode
    aliases: tuple[str, ...]
    background: str  # webp filename; use map_background() to build a width-specific path


MAP_BACKGROUND_WIDTHS: tuple[int, ...] = (1920, 1280, 640, 320)


def _resolve_pkg_root() -> Path:
    # In a built wheel, hatchling's force-include places heroes.json inside the package.
    # In an editable install, the data stays at the repo root (one level up).
    candidate = Path(str(files("ow_data")))
    if (candidate / "heroes.json").exists():
        return candidate
    return candidate.parent


_pkg_root: Path = _resolve_pkg_root()


def _load_json(name: str):
    with (_pkg_root / name).open("r", encoding="utf-8") as f:
        return json.load(f)


def _parse_heroes(raw: list[dict]) -> tuple[Hero, ...]:
    return tuple(
        Hero(
            name=h["name"],
            slug=h["slug"],
            role=h["role"],
            subrole=h["subrole"],
            portrait=h["portrait"],
            icon=h["icon"],
            color=h["color"],
            aliases=tuple(h.get("aliases", [])),
            perks=tuple(
                Perk(
                    name=p["name"],
                    slug=p["slug"],
                    tier=p["tier"],
                    slot=p["slot"],
                    icon=p["icon"],
                    added_on=p.get("added_on"),
                    removed_on=p.get("removed_on"),
                )
                for p in h["perks"]
            ),
        )
        for h in raw
    )


def _parse_maps(raw: list[dict]) -> tuple[GameMap, ...]:
    return tuple(
        GameMap(
            name=m["name"],
            mode=m["mode"],
            aliases=tuple(m.get("aliases", [])),
            background=m["background"],
        )
        for m in raw
    )


heroes: tuple[Hero, ...] = _parse_heroes(_load_json("heroes.json"))
maps: tuple[GameMap, ...] = _parse_maps(_load_json("maps.json"))

ALL_HERO_NAMES: tuple[str, ...] = tuple(h.name for h in heroes)
ALL_MAP_NAMES: tuple[str, ...] = tuple(m.name for m in maps)


def _build_lookup(items):
    lookup = {}
    for item in items:
        lookup[item.name.lower()] = item
        for alias in item.aliases:
            lookup[alias.lower()] = item
    return lookup


_HERO_LOOKUP: dict[str, Hero] = _build_lookup(heroes)
_MAP_LOOKUP: dict[str, GameMap] = _build_lookup(maps)


def get_hero(name_or_alias: str) -> Hero | None:
    return _HERO_LOOKUP.get(name_or_alias.lower())


def get_map(name_or_alias: str) -> GameMap | None:
    return _MAP_LOOKUP.get(name_or_alias.lower())


def normalize_hero_name(input_: str) -> str | None:
    hero = _HERO_LOOKUP.get(input_.lower())
    return hero.name if hero else None


def normalize_map_name(input_: str) -> str | None:
    game_map = _MAP_LOOKUP.get(input_.lower())
    return game_map.name if game_map else None


def is_perk_active(perk: Perk, date: str) -> bool:
    """True iff the perk was active on the given ISO date (YYYY-MM-DD)."""
    if perk.added_on is not None and perk.added_on > date:
        return False
    if perk.removed_on is not None and perk.removed_on <= date:
        return False
    return True


def get_active_perks(hero: Hero, date: str | None = None) -> tuple[Perk, ...]:
    """Perks active on the given ISO date (defaults to today)."""
    d = date if date is not None else _date.today().isoformat()
    return tuple(p for p in hero.perks if is_perk_active(p, d))


def get_perk(hero: Hero, perk_slug: str) -> Perk | None:
    """Look up a perk by slug regardless of lifecycle (for historic matches)."""
    for p in hero.perks:
        if p.slug == perk_slug:
            return p
    return None


def map_background(game_map: GameMap, width: int) -> str:
    """Package-relative path to a map's background at the given width.

    Pass the result to asset_path() for an absolute path. Width should be one
    of MAP_BACKGROUND_WIDTHS.
    """
    return f"map_backgrounds/{width}/{game_map.background}"


def asset_path(relative_path: str) -> Path:
    """Absolute path to a packaged asset (e.g., 'hero_portraits/DVa.png')."""
    return _pkg_root / relative_path


hero_portraits_dir: Path = _pkg_root / "hero_portraits"
hero_icons_dir: Path = _pkg_root / "hero_icons"
perks_dir: Path = _pkg_root / "perks"
map_backgrounds_dir: Path = _pkg_root / "map_backgrounds"
