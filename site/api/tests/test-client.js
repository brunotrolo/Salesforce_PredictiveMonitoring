import { jest } from "@jest/globals";
import {
  fetchLatestSnapshot,
  fetchLatestSnapshotFromTrace,
  fetchDay,
  fetchRecentSnapshots,
  fetchTrace,
  fetchWorkflowRuns,
  listDayFolders,
} from "../client.js";

beforeEach(() => {
  global.fetch = jest.fn();
});

afterEach(() => {
  jest.restoreAllMocks();
});

function jsonRes(body, ok = true) {
  return { ok, status: ok ? 200 : 404, json: () => Promise.resolve(body) };
}

describe("listDayFolders", () => {
  test("returns sorted+reversed day folder names", async () => {
    global.fetch.mockResolvedValueOnce(
      jsonRes([{ type: "dir", name: "2026-08-15" }, { type: "dir", name: "2026-08-16" }, {
        type: "file",
        name: "README.md",
      }])
    );
    const days = await listDayFolders();
    expect(days).toEqual(["2026-08-16", "2026-08-15"]);
  });

  test("truncates to limit", async () => {
    global.fetch.mockResolvedValueOnce(
      jsonRes([
        { type: "dir", name: "2026-08-15" },
        { type: "dir", name: "2026-08-16" },
        { type: "dir", name: "2026-08-17" },
        { type: "dir", name: "2026-08-18" },
      ])
    );
    expect(await listDayFolders(2)).toEqual(["2026-08-18", "2026-08-17"]);
  });

  test("returns [] when API fails", async () => {
    global.fetch.mockResolvedValueOnce(jsonRes(undefined, false));
    expect(await listDayFolders()).toEqual([]);
  });

  test("returns [] on network error", async () => {
    global.fetch.mockRejectedValueOnce(new Error("network down"));
    expect(await listDayFolders()).toEqual([]);
  });
});

describe("fetchDay", () => {
  test("fetches and parses each snapshot file, newest first", async () => {
    global.fetch
      .mockResolvedValueOnce(
        jsonRes([
          { type: "file", name: "2026-08-15T09-00-00Z.json" },
          { type: "file", name: "2026-08-15T10-00-00Z.json" },
        ])
      )
      .mockResolvedValueOnce(
        jsonRes({ risk_score: 0.5, timestamp: "2026-08-15T10:00:00Z" })
      )
      .mockResolvedValueOnce(
        jsonRes({ risk_score: 0.3, timestamp: "2026-08-15T09:00:00Z" })
      );
    const shots = await fetchDay("2026-08-15");
    expect(shots).toHaveLength(2);
    expect(shots[0].risk_score).toBe(0.5);
    expect(shots[1].risk_score).toBe(0.3);
  });

  test("returns [] when API fails", async () => {
    global.fetch.mockResolvedValueOnce(jsonRes(undefined, false));
    expect(await fetchDay("2026-08-15")).toEqual([]);
  });

  test("returns [] on network error", async () => {
    global.fetch.mockRejectedValueOnce(new Error("down"));
    expect(await fetchDay("2026-08-15")).toEqual([]);
  });
});

describe("fetchLatestSnapshot", () => {
  const liveSnapshot = { risk_score: 0.83, timestamp: "2026-08-16T10:00:00Z", alerts: [] };

  test("prefers the trace.json path (no rate-limit API call)", async () => {
    const traceUrl = "https://raw.githubusercontent.com/brunotrolo/Salesforce_PredictiveMonitoring/data/trace.json";
    const snapshotUrl = "https://raw.githubusercontent.com/brunotrolo/Salesforce_PredictiveMonitoring/data/2026-08-16/2026-08-16T10-00-00Z.json";
    global.fetch
      .mockResolvedValueOnce(
        jsonRes([
          { timestamp: "2026-08-16T09:00:00Z", risk_score: 0.1, snapshot_raw: snapshotUrl },
          { timestamp: "2026-08-16T10:00:00Z", risk_score: 0.83, snapshot_raw: snapshotUrl },
        ])
      )
      .mockResolvedValueOnce(jsonRes(liveSnapshot));
    const snap = await fetchLatestSnapshot();
    expect(snap).toEqual(liveSnapshot);
    // Only 2 fetches: trace.json + the snapshot. NO api.github.com calls.
    expect(global.fetch).toHaveBeenCalledTimes(2);
    expect(global.fetch.mock.calls[0][0]).toBe(traceUrl);
    expect(global.fetch.mock.calls[1][0]).toBe(snapshotUrl);
  });

  test("falls back to listing day folders when trace is empty", async () => {
    global.fetch
      .mockResolvedValueOnce(jsonRes([]))
      .mockResolvedValueOnce(jsonRes([{ type: "dir", name: "2026-08-16" }]))
      .mockResolvedValueOnce(
        jsonRes([{ type: "file", name: "2026-08-16T10-00-00Z.json" }])
      )
      .mockResolvedValueOnce(jsonRes(liveSnapshot));
    const snap = await fetchLatestSnapshot();
    expect(snap).toEqual(liveSnapshot);
  });

  test("falls back to listing day folders when trace.json fetch fails", async () => {
    global.fetch
      .mockResolvedValueOnce(jsonRes(undefined, false))
      .mockResolvedValueOnce(jsonRes([{ type: "dir", name: "2026-08-16" }]))
      .mockResolvedValueOnce(
        jsonRes([{ type: "file", name: "2026-08-16T10-00-00Z.json" }])
      )
      .mockResolvedValueOnce(jsonRes(liveSnapshot));
    const snap = await fetchLatestSnapshot();
    expect(snap).toEqual(liveSnapshot);
  });

  test("falls back to mock data when no days exist", async () => {
    global.fetch
      .mockResolvedValueOnce(jsonRes([]))                // trace.json empty
      .mockResolvedValueOnce(jsonRes([]));                // listDayFolders empty
    const snap = await fetchLatestSnapshot();
    expect(snap.risk_score).toBe(0.42);
  });

  test("falls back to mock data when network fails", async () => {
    global.fetch.mockRejectedValueOnce(new Error("offline"));
    const snap = await fetchLatestSnapshot();
    expect(snap.risk_score).toBe(0.42);
  });
});

describe("fetchLatestSnapshotFromTrace", () => {
  test("returns null when trace.json is missing", async () => {
    global.fetch.mockResolvedValueOnce(jsonRes(undefined, false));
    expect(await fetchLatestSnapshotFromTrace()).toBeNull();
  });

  test("returns null when trace.json is empty", async () => {
    global.fetch.mockResolvedValueOnce(jsonRes([]));
    expect(await fetchLatestSnapshotFromTrace()).toBeNull();
  });

  test("returns null when the last entry has no snapshot_raw", async () => {
    global.fetch.mockResolvedValueOnce(jsonRes([{ timestamp: "x", risk_score: 0.1 }]));
    expect(await fetchLatestSnapshotFromTrace()).toBeNull();
  });

  test("returns the parsed snapshot from snapshot_raw URL", async () => {
    const snapshotUrl = "https://raw.githubusercontent.com/brunotrolo/Salesforce_PredictiveMonitoring/data/x/y.json";
    const snap = { risk_score: 0.5, timestamp: "2026-08-16T10:00:00Z" };
    global.fetch
      .mockResolvedValueOnce(jsonRes([{ snapshot_raw: snapshotUrl }]))
      .mockResolvedValueOnce(jsonRes(snap));
    expect(await fetchLatestSnapshotFromTrace()).toEqual(snap);
  });

  test("returns null when snapshot_raw fetch fails", async () => {
    global.fetch
      .mockResolvedValueOnce(jsonRes([{ snapshot_raw: "https://nope.example/missing.json" }]))
      .mockResolvedValueOnce(jsonRes(undefined, false));
    expect(await fetchLatestSnapshotFromTrace()).toBeNull();
  });

  test("returns null when the snapshot body is not valid JSON", async () => {
    const snapshotUrl = "https://raw.githubusercontent.com/brunotrolo/Salesforce_PredictiveMonitoring/data/x/y.json";
    global.fetch
      .mockResolvedValueOnce(jsonRes([{ snapshot_raw: snapshotUrl }]))
      .mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.reject(new SyntaxError("bad")) });
    expect(await fetchLatestSnapshotFromTrace()).toBeNull();
  });
});

describe("fetchRecentSnapshots", () => {
  test("uses trace.json entries to resolve snapshots via snapshot_raw", async () => {
    const url1 = "https://raw.githubusercontent.com/brunotrolo/Salesforce_PredictiveMonitoring/data/2026-08-16/b.json";
    const url2 = "https://raw.githubusercontent.com/brunotrolo/Salesforce_PredictiveMonitoring/data/2026-08-16/a.json";
    global.fetch
      .mockResolvedValueOnce(
        jsonRes([
          { timestamp: "2026-08-16T09:00:00Z", snapshot_raw: url2 },
          { timestamp: "2026-08-16T10:00:00Z", snapshot_raw: url1 },
        ])
      )
      .mockResolvedValueOnce(jsonRes({ id: 1 }))
      .mockResolvedValueOnce(jsonRes({ id: 2 }));
    const snaps = await fetchRecentSnapshots();
    expect(snaps).toHaveLength(2);
    // Newest first
    expect(snaps[0].id).toBe(1);
    expect(snaps[1].id).toBe(2);
  });

  test("skips entries without snapshot_raw and continues", async () => {
    const url1 = "https://raw.githubusercontent.com/brunotrolo/Salesforce_PredictiveMonitoring/data/a.json";
    global.fetch
      .mockResolvedValueOnce(
        jsonRes([
          { timestamp: "2026-08-16T09:00:00Z" /* no snapshot_raw */ },
          { timestamp: "2026-08-16T10:00:00Z", snapshot_raw: url1 },
        ])
      )
      .mockResolvedValueOnce(jsonRes({ id: 9 }));
    const snaps = await fetchRecentSnapshots();
    expect(snaps).toHaveLength(1);
    expect(snaps[0].id).toBe(9);
  });

  test("falls back to listing day folders when trace.json fails", async () => {
    global.fetch
      .mockResolvedValueOnce(jsonRes(undefined, false))
      .mockResolvedValueOnce(
        jsonRes([{ type: "dir", name: "2026-08-16" }, { type: "dir", name: "2026-08-15" }])
      )
      .mockResolvedValueOnce(
        jsonRes([
          { type: "file", name: "a.json" },
          { type: "file", name: "b.json" },
        ])
      )
      .mockResolvedValueOnce(jsonRes({ id: 2 }))
      .mockResolvedValueOnce(jsonRes({ id: 1 }))
      .mockResolvedValueOnce(jsonRes([{ type: "file", name: "c.json" }]))
      .mockResolvedValueOnce(jsonRes({ id: 3 }));
    const snaps = await fetchRecentSnapshots();
    expect(snaps).toHaveLength(3);
    expect(snaps[0].id).toBe(2);
    expect(snaps[2].id).toBe(3);
  });

  test("returns single mock snapshot when no data exists", async () => {
    global.fetch
      .mockResolvedValueOnce(jsonRes([]))
      .mockResolvedValueOnce(jsonRes([]));
    const snaps = await fetchRecentSnapshots();
    expect(snaps).toHaveLength(1);
    expect(snaps[0].risk_score).toBe(0.42);
  });
});
describe("fetchWorkflowRuns", () => {
  test("returns runs array with rateLimited=false when successful", async () => {
    const runs = [
      { id: 1, status: "in_progress", started_at: "2026-08-19T12:00:00Z" },
    ];
    global.fetch.mockResolvedValueOnce(jsonRes({ workflow_runs: runs }));
    const got = await fetchWorkflowRuns("ghp_token");
    expect(got).toEqual({ runs, rateLimited: false });
    const opts = global.fetch.mock.calls[0][1];
    expect(opts.headers.Authorization).toBe("Bearer ghp_token");
  });

  test("returns rateLimited=true on 403", async () => {
    global.fetch.mockResolvedValueOnce({ ok: false, status: 403 });
    const got = await fetchWorkflowRuns("tok");
    expect(got).toEqual({ runs: null, rateLimited: true });
  });

  test("returns rateLimited=true on 429", async () => {
    global.fetch.mockResolvedValueOnce({ ok: false, status: 429 });
    const got = await fetchWorkflowRuns("tok");
    expect(got).toEqual({ runs: null, rateLimited: true });
  });

  test("returns rateLimited=false on other HTTP error", async () => {
    global.fetch.mockResolvedValueOnce(jsonRes(undefined, false));
    const got = await fetchWorkflowRuns("tok");
    expect(got).toEqual({ runs: null, rateLimited: false });
  });

  test("returns rateLimited=false on network error", async () => {
    global.fetch.mockRejectedValueOnce(new Error("down"));
    const got = await fetchWorkflowRuns("tok");
    expect(got).toEqual({ runs: null, rateLimited: false });
  });

  test("works without a token (public read path)", async () => {
    global.fetch.mockResolvedValueOnce(jsonRes({ workflow_runs: [{ id: 1 }] }));
    const got = await fetchWorkflowRuns(null);
    expect(got).toEqual({ runs: [{ id: 1 }], rateLimited: false });
    const opts = global.fetch.mock.calls[0][1];
    expect(opts.headers).toBeUndefined();
  });
});

describe("fetchTrace", () => {
  test("returns live entries from the data branch", async () => {
    const trace = [
      { timestamp: "2026-08-15T10:00:00Z", risk_score: 0.1 },
      { timestamp: "2026-08-15T10:05:00Z", risk_score: 0.2 },
    ];
    global.fetch.mockResolvedValueOnce(jsonRes(trace));
    expect(await fetchTrace()).toEqual({ entries: trace, source: "live" });
  });

  test("returns empty source on HTTP error, never mock data", async () => {
    global.fetch.mockResolvedValueOnce(jsonRes(undefined, false));
    const trace = await fetchTrace();
    expect(trace).toEqual({ entries: [], source: "none" });
  });

  test("returns empty source on network error, never mock data", async () => {
    global.fetch.mockRejectedValueOnce(new Error("down"));
    const trace = await fetchTrace();
    expect(trace).toEqual({ entries: [], source: "none" });
  });

test("returns empty source on empty or malformed body, never mock data", async () => {
    global.fetch.mockResolvedValueOnce(jsonRes([]));
    expect(await fetchTrace()).toEqual({ entries: [], source: "none" });
    global.fetch.mockResolvedValueOnce(jsonRes("not-json"));
    expect(await fetchTrace()).toEqual({ entries: [], source: "none" });
  });
});
