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
}

export interface Hero {
  name: string;
  slug: string;
  role: Role;
  subrole: string;
  portrait: string;
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
