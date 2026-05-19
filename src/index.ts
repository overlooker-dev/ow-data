import heroesJson from "../heroes.json" with { type: "json" };
import mapsJson from "../maps.json" with { type: "json" };

export type Role = "tank" | "damage" | "support";
export type PerkTier = "minor" | "major";
export type PerkSlot = 1 | 2 | 3 | 4;
export type MapMode =
  | "control"
  | "escort"
  | "hybrid"
  | "push"
  | "flashpoint"
  | "clash"
  | "payload_race"
  | "assault"
  | "capture_the_flag"
  | "deathmatch"
  | "elimination"
  | "workshop"
  | "training";

export interface Perk {
  name: string;
  slug: string;
  tier: PerkTier;
  slot: PerkSlot;
  icon: string;
  /** ISO date (YYYY-MM-DD) the perk went live in-game. Absent = always-existed. */
  added_on?: string;
  /** ISO date (YYYY-MM-DD) the perk was removed in-game. Absent = currently active. */
  removed_on?: string;
}

export interface Hero {
  name: string;
  slug: string;
  role: Role;
  subrole: string;
  portrait: string;
  /** Accent color as a `#RRGGBB` hex string. Used by clients for hero-keyed UI (e.g., swap timelines). */
  color: string;
  aliases: string[];
  perks: Perk[];
}

export interface GameMap {
  name: string;
  mode: MapMode;
  aliases: string[];
}

export const heroes: Hero[] = heroesJson as Hero[];
export const maps: GameMap[] = mapsJson as GameMap[];

export const ALL_HERO_NAMES: string[] = heroes.map((h) => h.name);
export const ALL_MAP_NAMES: string[] = maps.map((m) => m.name);

function buildLookup<T extends { name: string; aliases: string[] }>(items: readonly T[]): Map<string, T> {
  const lookup = new Map<string, T>();
  for (const item of items) {
    lookup.set(item.name.toLowerCase(), item);
    for (const alias of item.aliases) lookup.set(alias.toLowerCase(), item);
  }
  return lookup;
}

const _heroLookup = buildLookup(heroes);
const _mapLookup = buildLookup(maps);

export function getHero(nameOrAlias: string): Hero | undefined {
  return _heroLookup.get(nameOrAlias.toLowerCase());
}

export function getMap(nameOrAlias: string): GameMap | undefined {
  return _mapLookup.get(nameOrAlias.toLowerCase());
}

export function normalizeHeroName(input: string): string | undefined {
  return _heroLookup.get(input.toLowerCase())?.name;
}

export function normalizeMapName(input: string): string | undefined {
  return _mapLookup.get(input.toLowerCase())?.name;
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

/** True iff the perk was active on the given ISO date (`YYYY-MM-DD`). */
export function isPerkActive(perk: Perk, date: string): boolean {
  if (perk.added_on && perk.added_on > date) return false;
  if (perk.removed_on && perk.removed_on <= date) return false;
  return true;
}

/** Perks active on the given ISO date (defaults to today). */
export function getActivePerks(hero: Hero, date?: string): Perk[] {
  const d = date ?? todayIso();
  return hero.perks.filter((p) => isPerkActive(p, d));
}

/** Look up a perk by slug regardless of lifecycle (for rendering historic matches). */
export function getPerk(hero: Hero, perkSlug: string): Perk | undefined {
  return hero.perks.find((p) => p.slug === perkSlug);
}
