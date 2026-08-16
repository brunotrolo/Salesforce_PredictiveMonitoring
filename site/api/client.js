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
 * All credentials-free: reads the PUBLIC raw URL of the data branch
 * (the repo is public; no tokens are ever embedded in client code).
 */

import { mockMonitoringData, mockEmptyData } from "../monitoring/mock-data.js";

const REPO_OWNER = "brunotrolo";
const REPO_NAME = "Salesforce_PredictiveMonitoring";
const DATA_BRANCH = "data";
const RAW_BASE = `https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/${DATA_BRANCH}`;

/** Fetch with a short timeout so the dashboard never hangs waiting on GitHub. */
async function fetchTimeout(url, ms = 5000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  try {
    const res = await fetch(url, { signal: controller.signal });
    return res;
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

/** List the newest day folder names by querying the GitHub Contents API. */
export async function listDayFolders(limit = 7) {
  const api = `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/data?ref=${DATA_BRANCH}`;
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
 * Return the single most recent snapshot across all day folders,
 * or `mockMonitoringData` when the data branch is empty / unreachable.
 */
export async function fetchLatestSnapshot() {
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
 */
export async function fetchRecentSnapshots(limit = 12) {
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

export { mockEmptyData };