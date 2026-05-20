// Validates heroes.json, maps.json, and the on-disk asset tree.
// Collects all errors, then exits 1 if any were found.
// Run: `npm run validate` (uses node --experimental-strip-types).

import { readFileSync, existsSync, readdirSync, statSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");

interface Perk {
  name: string;
  slug: string;
  tier: "minor" | "major";
  slot: 1 | 2 | 3 | 4;
  icon: string;
  added_on?: string;
  removed_on?: string;
}
interface Hero {
  name: string;
  slug: string;
  role: string;
  subrole: string;
  portrait: string;
  color: string;
  aliases: string[];
  perks: Perk[];
}
interface GameMap {
  name: string;
  mode: string;
  aliases: string[];
  background: string;
}

const heroes: Hero[] = JSON.parse(readFileSync(resolve(repoRoot, "heroes.json"), "utf-8"));
const maps: GameMap[] = JSON.parse(readFileSync(resolve(repoRoot, "maps.json"), "utf-8"));

const VALID_ROLES = new Set(["tank", "damage", "support"]);
const VALID_MODES = new Set([
  "control", "escort", "hybrid", "push", "flashpoint", "clash",
  "payload_race",
  "assault", "capture_the_flag", "deathmatch", "elimination",
  "workshop", "training",
]);

const errors: string[] = [];
const err = (msg: string): void => { errors.push(msg); };

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;
const HEX_COLOR = /^#[0-9a-fA-F]{6}$/;
const today = new Date().toISOString().slice(0, 10);
const NEG_INF = "0000-00-00";
const POS_INF = "9999-99-99";

const referencedPortraits = new Set<string>();
const referencedIcons = new Set<string>();

const heroSlugs = new Set<string>();
const heroLookup = new Map<string, string>(); // lowercase name|alias -> canonical name

for (const h of heroes) {
  if (heroSlugs.has(h.slug)) err(`hero slug duplicated: "${h.slug}"`);
  heroSlugs.add(h.slug);

  if (!VALID_ROLES.has(h.role)) err(`hero "${h.slug}": invalid role "${h.role}"`);

  if (!existsSync(resolve(repoRoot, h.portrait))) {
    err(`hero "${h.slug}": missing portrait file ${h.portrait}`);
  }
  referencedPortraits.add(h.portrait);

  if (!HEX_COLOR.test(h.color)) {
    err(`hero "${h.slug}": color "${h.color}" is not a #RRGGBB hex string`);
  }

  const nameKey = h.name.toLowerCase();
  if (heroLookup.has(nameKey)) {
    err(`hero "${h.slug}": name "${h.name}" collides with existing entry "${heroLookup.get(nameKey)}"`);
  } else {
    heroLookup.set(nameKey, h.name);
  }

  for (const alias of h.aliases) {
    const key = alias.toLowerCase();
    if (key === nameKey) {
      err(`hero "${h.slug}": alias "${alias}" duplicates its own name (CLAUDE.md: do not include name in aliases)`);
    } else if (heroLookup.has(key)) {
      err(`hero "${h.slug}": alias "${alias}" collides with existing entry "${heroLookup.get(key)}"`);
    } else {
      heroLookup.set(key, h.name);
    }
  }

  const perkSlugs = new Set<string>();
  const bySlot = new Map<number, Perk[]>();
  for (const p of h.perks) {
    if (perkSlugs.has(p.slug)) err(`hero "${h.slug}": duplicate perk slug "${p.slug}" (slugs are unique across history — never reuse)`);
    perkSlugs.add(p.slug);

    const expectedTier = p.slot <= 2 ? "minor" : "major";
    if (p.tier !== expectedTier) {
      err(`hero "${h.slug}": perk "${p.slug}" slot ${p.slot} has tier "${p.tier}", expected "${expectedTier}"`);
    }

    if (p.added_on !== undefined && !ISO_DATE.test(p.added_on)) {
      err(`hero "${h.slug}": perk "${p.slug}" added_on "${p.added_on}" is not ISO YYYY-MM-DD`);
    }
    if (p.removed_on !== undefined && !ISO_DATE.test(p.removed_on)) {
      err(`hero "${h.slug}": perk "${p.slug}" removed_on "${p.removed_on}" is not ISO YYYY-MM-DD`);
    }
    if (p.added_on && p.removed_on && p.added_on >= p.removed_on) {
      err(`hero "${h.slug}": perk "${p.slug}" added_on "${p.added_on}" must be before removed_on "${p.removed_on}"`);
    }

    if (!existsSync(resolve(repoRoot, p.icon))) {
      err(`hero "${h.slug}": missing perk icon ${p.icon}`);
    }
    referencedIcons.add(p.icon);

    if (!bySlot.has(p.slot)) bySlot.set(p.slot, []);
    bySlot.get(p.slot)!.push(p);
  }

  // Per-slot lifecycle: active windows must not overlap, and exactly one must be
  // currently active (no removed_on, added_on <= today).
  for (const slot of [1, 2, 3, 4]) {
    const perks = bySlot.get(slot) ?? [];
    if (perks.length === 0) {
      err(`hero "${h.slug}": no perks ever defined for slot ${slot}`);
      continue;
    }

    const sorted = [...perks].sort(
      (a, b) => (a.added_on ?? NEG_INF).localeCompare(b.added_on ?? NEG_INF),
    );
    for (let i = 1; i < sorted.length; i++) {
      const prev = sorted[i - 1]!;
      const curr = sorted[i]!;
      const prevEnd = prev.removed_on ?? POS_INF;
      const currStart = curr.added_on ?? NEG_INF;
      if (prevEnd > currStart) {
        err(`hero "${h.slug}": slot ${slot} perks "${prev.slug}" and "${curr.slug}" have overlapping active windows`);
      }
    }

    const active = perks.filter(
      (p) => (p.added_on ?? NEG_INF) <= today && (p.removed_on ?? POS_INF) > today,
    );
    if (active.length === 0) {
      err(`hero "${h.slug}": slot ${slot} has no perk active on ${today}`);
    } else if (active.length > 1) {
      err(`hero "${h.slug}": slot ${slot} has ${active.length} perks active on ${today}: ${active.map((p) => p.slug).join(", ")}`);
    }
  }
}

const MAP_BACKGROUND_WIDTHS = [1920, 1280, 640, 320];
const referencedBackgrounds = new Set<string>();

const mapNames = new Set<string>();
const mapLookup = new Map<string, string>();

for (const m of maps) {
  if (!VALID_MODES.has(m.mode)) err(`map "${m.name}": invalid mode "${m.mode}"`);

  if (mapNames.has(m.name)) err(`map name duplicated: "${m.name}"`);
  mapNames.add(m.name);

  for (const width of MAP_BACKGROUND_WIDTHS) {
    const rel = `map_backgrounds/${width}/${m.background}`;
    if (!existsSync(resolve(repoRoot, rel))) {
      err(`map "${m.name}": missing background file ${rel}`);
    }
    referencedBackgrounds.add(rel);
  }

  const nameKey = m.name.toLowerCase();
  if (mapLookup.has(nameKey)) {
    err(`map "${m.name}": collides with existing entry "${mapLookup.get(nameKey)}"`);
  } else {
    mapLookup.set(nameKey, m.name);
  }

  for (const alias of m.aliases) {
    const key = alias.toLowerCase();
    if (key === nameKey) {
      err(`map "${m.name}": alias "${alias}" duplicates its own name`);
    } else if (mapLookup.has(key)) {
      err(`map "${m.name}": alias "${alias}" collides with existing entry "${mapLookup.get(key)}"`);
    } else {
      mapLookup.set(key, m.name);
    }
  }
}

// Orphan files on disk (excludes .gitkeep and hidden files).
const portraitsDir = resolve(repoRoot, "hero_portraits");
if (existsSync(portraitsDir)) {
  for (const f of readdirSync(portraitsDir)) {
    if (f.startsWith(".")) continue;
    const rel = `hero_portraits/${f}`;
    if (!referencedPortraits.has(rel)) err(`orphan portrait on disk: ${rel}`);
  }
}

const perksDir = resolve(repoRoot, "perks");
if (existsSync(perksDir)) {
  for (const heroDir of readdirSync(perksDir)) {
    if (heroDir.startsWith(".")) continue;
    const abs = resolve(perksDir, heroDir);
    if (!statSync(abs).isDirectory()) continue;
    for (const f of readdirSync(abs)) {
      if (f.startsWith(".")) continue;
      const rel = `perks/${heroDir}/${f}`;
      if (!referencedIcons.has(rel)) err(`orphan perk icon on disk: ${rel}`);
    }
  }
}

for (const width of MAP_BACKGROUND_WIDTHS) {
  const dir = resolve(repoRoot, `map_backgrounds/${width}`);
  if (!existsSync(dir)) continue;
  for (const f of readdirSync(dir)) {
    if (f.startsWith(".")) continue;
    const rel = `map_backgrounds/${width}/${f}`;
    if (!referencedBackgrounds.has(rel)) err(`orphan map background on disk: ${rel}`);
  }
}

if (errors.length > 0) {
  console.error(`validation failed: ${errors.length} error(s)`);
  for (const e of errors) console.error(`  - ${e}`);
  process.exit(1);
}

console.log(
  `ok — ${heroes.length} heroes, ${maps.length} maps, ${referencedPortraits.size} portraits, ${referencedIcons.size} perk icons, ${referencedBackgrounds.size} map backgrounds`,
);
