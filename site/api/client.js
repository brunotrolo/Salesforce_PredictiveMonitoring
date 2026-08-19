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
 * The ONLY token-aware calls are the manual-refresh helpers
 * (dispatchWorkflow / fetchWorkflowRuns / validateToken): they take the
 * user's personal token from localStorage at call time and never persist
 * it anywhere but that browser profile.
 */

import { mockMonitoringData, mockEmptyData, mockTraceData } from "../monitoring/mock-data.js";

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
 * Trigger collect.yml manually via the Actions REST API (workflow_dispatch).
 * Requires a personal token with "Actions: read/write" on this repo.
 * Resolves { ok, status, error } — 204 means the run was queued.
 */
export async function dispatchWorkflow(token) {
  try {
    const res = await fetchTimeout(
      `${GH_API}/actions/workflows/collect.yml/dispatches`,
      8000,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "application/vnd.github+json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ ref: "main" }),
      }
    );
    if (!res) return { ok: false, status: 0, error: "sem resposta de rede" };
    if (res.status === 204) return { ok: true, status: 204, error: null };
    let message = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body && body.message) message = body.message;
    } catch {
      /* keep generic message */
    }
    return { ok: false, status: res.status, error: message };
  } catch (err) {
    return { ok: false, status: 0, error: String((err && err.message) || err) };
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
    headers ? { headers } : {}
  );
  if (!res || !res.ok) return null;
  try {
    const data = await res.json();
    return data && Array.isArray(data.workflow_runs) ? data.workflow_runs : null;
  } catch {
    return null;
  }
}

/**
 * Cheap validation of a saved token: one read call against the Actions API.
 * True only when the token is accepted and has read access.
 */
export async function validateToken(token) {
  const res = await fetchTimeout(
    `${GH_API}/actions/workflows/collect.yml/runs?per_page=1`,
    8000,
    {
      headers: { Authorization: `Bearer ${token}`, Accept: "application/vnd.github+json" },
    }
  );
  return Boolean(res && res.ok);
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

export { mockEmptyData };