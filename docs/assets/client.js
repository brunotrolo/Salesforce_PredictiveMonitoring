/**
 * GENERATED MIRROR — do not edit by hand.
 * Source: site/api/client.js
 * Regenerate: node site/scripts/sync-dashboard.mjs
 */

/**
 * Live data fetcher for the monitoring dashboard.
 *
 * Reads the latest snapshot persisted by `.github/workflows/collect.yml`
 * from the `data/` branch (ADR-008: Git as datastore).
 *
 * Contract per SPECIFICATION.md §3.2:
 *   - fetchLatestSnapshot(): Promise<object|null>  -> most recent risk_scores.json
 *   - fetchDay(day): Promise<object[]>             -> all snapshots for a given day
 *   - Falls back to mock data when offline / no data branch yet.
 *
 * All credentials-free by default: reads the PUBLIC raw URL of the data
 * branch (the repo is public; no tokens are ever embedded in client code).
 * The ONLY token-aware call is fetchWorkflowRuns(): it takes the user's
 * personal token from localStorage at call time and never persists it
 * anywhere but that browser profile.
 *
 * Fetching strategy (see fetchLatestSnapshot):
 *   1. Primary: read trace.json via raw.githubusercontent.com (1 request, no
 *      rate limit, no CORS friction), then read the snapshot_raw URL from
 *      the last entry (1 more request, same path). Total: 2 requests.
 *   2. Fallback: list day folders via api.github.com and walk files
 *      (N+1 requests, subject to the 60/hr unauthenticated rate limit).
 *      Used only when trace.json is missing or empty (e.g. very first run).
 */

import { mockMonitoringData, mockEmptyData, mockTraceData } from "./mock-data.js";

const REPO_OWNER = "brunotrolo";
const REPO_NAME = "Salesforce_PredictiveMonitoring";
const DATA_BRANCH = "data";
const RAW_BASE = `https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/${DATA_BRANCH}`;
const GH_API = `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}`;

/** Fetch with a short timeout so the dashboard never hangs waiting on GitHub. */
export async function fetchTimeout(url, ms = 5000, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  try {
    const res = await fetch(url, { ...options, signal: controller.signal });
    return res;
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Newest workflow_dispatch run for collect.yml, or null on any error.
 * Uses the token when available (higher rate limit), otherwise the public
 * read-only endpoint.
 */
export async function fetchWorkflowRuns(token) {
  const headers = token
    ? { Authorization: `Bearer ${token}`, Accept: "application/vnd.github+json" }
    : undefined;
  const res = await fetchTimeout(
    `${GH_API}/actions/workflows/collect.yml/runs?event=workflow_dispatch&per_page=1`,
    7000,
    headers ? { headers } : undefined
  );
  if (!res) return { runs: null, rateLimited: false };
  if (res.status === 403 || res.status === 429)
    return { runs: null, rateLimited: true };
  if (!res.ok) return { runs: null, rateLimited: false };
  try {
    const data = await res.json();
    return {
      runs: Array.isArray(data.workflow_runs) ? data.workflow_runs : null,
      rateLimited: false,
    };
  } catch {
    return { runs: null, rateLimited: false };
  }
}

/** List the newest day folder names by querying the GitHub Contents API. */
export async function listDayFolders(limit = 7) {
  const api = `${GH_API}/contents/data?ref=${DATA_BRANCH}`;
  try {
    const res = await fetchTimeout(api);
    if (!res || !res.ok) return [];
    const entries = await res.json();
    return entries
      .filter((e) => e.type === "dir")
      .map((e) => e.name)
      .sort()
      .reverse()
      .slice(0, limit);
  } catch {
    return [];
  }
}

/**
 * Fetch every snapshot file under `data/<day>/` (timestamp-named .json files).
 * Returns an array of parsed snapshot objects, newest first.
 */
export async function fetchDay(day) {
  const api = `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/data/${day}?ref=${DATA_BRANCH}`;
  try {
    const res = await fetchTimeout(api);
    if (!res || !res.ok) return [];
    const entries = await res.json();
    const files = entries
      .filter((e) => e.type === "file" && e.name.endsWith(".json"))
      .sort((a, b) => (a.name < b.name ? 1 : -1));
    const snapshots = [];
    for (const file of files) {
      const fileRes = await fetchTimeout(`${RAW_BASE}/data/${day}/${file.name}`);
      if (fileRes && fileRes.ok) snapshots.push(await fileRes.json());
    }
    return snapshots;
  } catch {
    return [];
  }
}

/**
 * Resolve the latest snapshot via the rolling 24h trace.
 *
 * The backend persists the raw GitHub URL of every snapshot it writes to
 * the trace entry under `snapshot_raw` (see orchestrate._trace_entry_from_result).
 * Reading that URL through raw.githubusercontent.com is rate-limit-free
 * (CDN) and avoids the api.github.com Contents API entirely — that API
 * is the bottleneck (60 requests/hour for unauthenticated browsers).
 *
 * Returns the parsed snapshot or null if the trace is missing/empty/
 * malformed or the latest entry has no snapshot_raw.
 */
export async function fetchLatestSnapshotFromTrace() {
  const traceRes = await fetchTimeout(`${RAW_BASE}/trace.json`);
  if (!traceRes || !traceRes.ok) return null;
  let entries;
  try {
    entries = await traceRes.json();
  } catch {
    return null;
  }
  if (!Array.isArray(entries) || entries.length === 0) return null;
  // Trace is sorted oldest -> newest; the last entry is the latest cycle.
  const latest = entries[entries.length - 1];
  const url = latest && latest.snapshot_raw;
  if (!url || typeof url !== "string") return null;
  const snapRes = await fetchTimeout(url);
  if (!snapRes || !snapRes.ok) return null;
  try {
    return await snapRes.json();
  } catch {
    return null;
  }
}

/**
 * Return the single most recent snapshot across all day folders,
 * or `mockMonitoringData` when the data branch is empty / unreachable.
 *
 * Primary path (preferred): trace.json → snapshot_raw URL (2 raw requests,
 * no rate limit). Fallback: list day folders + walk files (rate-limited).
 */
export async function fetchLatestSnapshot() {
  const fromTrace = await fetchLatestSnapshotFromTrace();
  if (fromTrace) return fromTrace;
  const days = await listDayFolders();
  for (const day of days) {
    const snapshots = await fetchDay(day);
    if (snapshots.length > 0) return snapshots[0];
  }
  return mockMonitoringData;
}

/**
 * Roll-up of the last `limit` snapshots (newest first), useful for trend charts.
 * Falls back to a single mock snapshot when no live data exists.
 *
 * Strategy: read trace.json for the lightweight summary (one entry per
 * cycle, no rate limit), then dereference each entry's snapshot_raw for
 * the full snapshot only when we actually need it (the chart needs the
 * full record). Skips entries whose snapshot_raw is missing (defensive).
 */
export async function fetchRecentSnapshots(limit = 12) {
  const traceRes = await fetchTimeout(`${RAW_BASE}/trace.json`);
  if (traceRes && traceRes.ok) {
    try {
      const entries = await traceRes.json();
      if (Array.isArray(entries) && entries.length > 0) {
        const newest = entries.slice(-limit).reverse();
        const snapshots = [];
        for (const entry of newest) {
          if (!entry || !entry.snapshot_raw) continue;
          const res = await fetchTimeout(entry.snapshot_raw);
          if (res && res.ok) {
            try {
              snapshots.push(await res.json());
            } catch { /* skip malformed snapshot */ }
          }
        }
        if (snapshots.length > 0) return snapshots;
      }
    } catch { /* fall through to legacy path */ }
  }
  const days = await listDayFolders();
  const collected = [];
  for (const day of days) {
    if (collected.length >= limit) break;
    const dayShots = await fetchDay(day);
    collected.push(...dayShots);
    if (collected.length >= limit) break;
  }
  return collected.slice(0, limit).length
    ? collected.slice(0, limit)
    : [mockMonitoringData];
}

/**
 * Rolling 24h trace maintained by the backend: one entry per collection
 * cycle, stored at the data branch root as trace.json. Returns
 * { entries, source } — source is "live" when the file exists and parses,
 * "none" otherwise. Simulated data is NEVER returned as live: the trace
 * section must show an explicit empty state instead of mock events that
 * look like real analysis.
 */
export async function fetchTrace() {
  const res = await fetchTimeout(`${RAW_BASE}/trace.json`);
  if (!res || !res.ok) return { entries: [], source: "none" };
  try {
    const data = await res.json();
    if (!Array.isArray(data) || data.length === 0) {
      return { entries: [], source: "none" };
    }
    return { entries: data, source: "live" };
  } catch {
    return { entries: [], source: "none" };
  }
}

/**
 * Fetch failure markers for a set of ISO-date strings (YYYY-MM-DD).
 * Returns a Map<string, object> keyed by marker filename (without .json)
 * whose values are the parsed failure JSON.  Missing files are silently
 * skipped — the map only contains actual failure records.
 */
export async function fetchFailureMarkers(days) {
  const markers = new Map();
  if (!Array.isArray(days) || days.length === 0) return markers;
  const fetches = days.map(async (day) => {
    const api = `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/data/${day}/failures?ref=${DATA_BRANCH}`;
    try {
      const res = await fetchTimeout(api);
      if (!res || !res.ok) return;
      const entries = await res.json();
      if (!Array.isArray(entries)) return;
      for (const entry of entries) {
        if (entry.type !== "file" || !entry.name.endsWith(".failure.json")) continue;
        try {
          const fileRes = await fetchTimeout(`${RAW_BASE}/data/${day}/failures/${entry.name}`);
          if (fileRes && fileRes.ok) {
            markers.set(entry.name.replace(/\.json$/, ""), await fileRes.json());
          }
        } catch { /* skip unreadable marker */ }
      }
    } catch { /* day has no failures folder — expected */ }
  });
  await Promise.all(fetches);
  return markers;
}

export { mockEmptyData };