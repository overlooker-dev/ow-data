// Node-only helpers. Do not import from a browser/renderer bundle —
// this file pulls in `node:url` and `node:path` at top level.

import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");

/** Absolute filesystem path to a packaged asset (e.g., "hero_portraits/DVa.png"). */
export function assetPath(relativePath: string): string {
  return resolve(packageRoot, relativePath);
}
