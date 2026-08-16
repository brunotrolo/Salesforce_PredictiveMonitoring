#!/usr/bin/env node
/**
 * sync-dashboard.mjs
 *
 * GitHub Pages serves ONLY `main/docs` (classic Jekyll build). The canonical,
 * tested modules live under `site/`. This script mirrors them into
 * `docs/dashboard/assets/` so the published page works without duplicating
 * source of truth.
 *
 * Mirrors (with a "GENERATED" header):
 *   - site/api/client.js            -> docs/dashboard/assets/client.js
 *   - site/monitoring/mock-data.js  -> docs/dashboard/assets/mock-data.js
 *   - site/monitoring/dashboard.js  -> docs/dashboard/assets/dashboard.js
 *
 * The only rewrite: client.js imports mock data via "../monitoring/mock-data.js";
 * in the mirror the path must be "./mock-data.js".
 *
 * Usage:
 *   node site/scripts/sync-dashboard.mjs           # write mirrors
 *   node site/scripts/sync-dashboard.mjs --check   # fail if stale (CI)
 *
 * CI (test.yml, frontend job) runs `--check` so a hand-edit or a forgotten
 * sync breaks the build instead of silently drifting.
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const CHECK = process.argv.includes("--check");

const HEADER = `/**
 * GENERATED MIRROR — do not edit by hand.
 * Source: %s
 * Regenerate: node site/scripts/sync-dashboard.mjs
 */`;

const TARGETS = [
  {
    source: "site/api/client.js",
    target: "docs/dashboard/assets/client.js",
    rewrite: [
      [
        'import { mockMonitoringData, mockEmptyData } from "../monitoring/mock-data.js";',
        'import { mockMonitoringData, mockEmptyData } from "./mock-data.js";',
      ],
    ],
  },
  {
    source: "site/monitoring/mock-data.js",
    target: "docs/dashboard/assets/mock-data.js",
    rewrite: [],
  },
  {
    source: "site/monitoring/dashboard.js",
    target: "docs/dashboard/assets/dashboard.js",
    rewrite: [],
  },
];

function fail(message) {
  console.error(`[sync-dashboard] ${message}`);
  process.exit(1);
}

let dirty = false;

for (const { source, target, rewrite } of TARGETS) {
  const sourcePath = join(ROOT, source);
  const targetPath = join(ROOT, target);
  if (!existsSync(sourcePath)) fail(`source missing: ${source}`);

  let content = readFileSync(sourcePath, "utf8");
  for (const [from, to] of rewrite) {
    if (!content.includes(from)) {
      fail(`rewrite anchor not found in ${source}: ${from}`);
    }
    content = content.replace(from, to);
  }

  const relSource = relative(ROOT, sourcePath).split("\\").join("/");
  const generated = `${HEADER.replace("%s", relSource)}\n\n${content}`;
  const existing = existsSync(targetPath) ? readFileSync(targetPath, "utf8") : null;

  if (existing === generated) {
    console.log(`[sync-dashboard] ok: ${source} -> ${target}`);
    continue;
  }
  if (CHECK) fail(`stale mirror: ${target} (run node site/scripts/sync-dashboard.mjs)`);
  dirty = true;
  mkdirSync(dirname(targetPath), { recursive: true });
  writeFileSync(targetPath, generated);
  console.log(`[sync-dashboard] written: ${source} -> ${target}`);
}

if (dirty) console.log("[sync-dashboard] mirrors updated.");
else if (!CHECK) console.log("[sync-dashboard] mirrors already fresh.");
