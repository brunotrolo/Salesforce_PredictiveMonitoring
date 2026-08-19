import { jest } from "@jest/globals";
import {
  fetchLatestSnapshot,
  fetchDay,
  fetchRecentSnapshots,
  fetchTrace,
  fetchWorkflowRuns,
  dispatchWorkflow,
  validateToken,
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

  test("returns the most recent snapshot when data branch is populated", async () => {
    const earlier = { risk_score: 0.4, timestamp: "2026-08-16T09:00:00Z" };
    global.fetch
      .mockResolvedValueOnce(jsonRes([{ type: "dir", name: "2026-08-16" }]))
      .mockResolvedValueOnce(
        jsonRes([
          { type: "file", name: "2026-08-16T10-00-00Z.json" },
          { type: "file", name: "2026-08-16T09-00-00Z.json" },
        ])
      )
      .mockResolvedValueOnce(jsonRes(liveSnapshot))
      .mockResolvedValueOnce(jsonRes(earlier));
    const snap = await fetchLatestSnapshot();
    expect(snap).toEqual(liveSnapshot);
  });

  test("falls back to mock data when no days exist", async () => {
    global.fetch.mockResolvedValueOnce(jsonRes([]));
    const snap = await fetchLatestSnapshot();
    expect(snap.risk_score).toBe(0.42);
  });

  test("falls back to mock data when network fails", async () => {
    global.fetch.mockRejectedValueOnce(new Error("offline"));
    const snap = await fetchLatestSnapshot();
    expect(snap.risk_score).toBe(0.42);
  });
});

describe("fetchRecentSnapshots", () => {
  test("collects snapshots across days up to limit", async () => {
    global.fetch
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
    global.fetch.mockResolvedValueOnce(jsonRes([]));
    const snaps = await fetchRecentSnapshots();
    expect(snaps).toHaveLength(1);
    expect(snaps[0].risk_score).toBe(0.42);
  });
});
describe("dispatchWorkflow", () => {
  test("resolves ok on 204 (run queued)", async () => {
    global.fetch.mockResolvedValueOnce({ ok: true, status: 204, json: () => Promise.resolve({}) });
    const result = await dispatchWorkflow("ghp_token");
    expect(result.ok).toBe(true);
    expect(result.status).toBe(204);
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain("/actions/workflows/collect.yml/dispatches");
    expect(opts.method).toBe("POST");
    expect(opts.headers.Authorization).toBe("Bearer ghp_token");
    expect(JSON.parse(opts.body)).toEqual({ ref: "main" });
  });

  test("returns not ok with GitHub message on 401", async () => {
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: () => Promise.resolve({ message: "Bad credentials" }),
    });
    const result = await dispatchWorkflow("bad_token");
    expect(result.ok).toBe(false);
    expect(result.status).toBe(401);
    expect(result.error).toBe("Bad credentials");
  });

  test("returns not ok with generic error on network failure", async () => {
    global.fetch.mockRejectedValueOnce(new Error("offline"));
    const result = await dispatchWorkflow("tok");
    expect(result.ok).toBe(false);
    expect(result.status).toBe(0);
  });
});

describe("fetchWorkflowRuns", () => {
  test("returns the runs array with token header", async () => {
    const runs = [
      { id: 1, status: "in_progress", started_at: "2026-08-19T12:00:00Z" },
    ];
    global.fetch.mockResolvedValueOnce(jsonRes({ workflow_runs: runs }));
    const got = await fetchWorkflowRuns("ghp_token");
    expect(got).toEqual(runs);
    const opts = global.fetch.mock.calls[0][1];
    expect(opts.headers.Authorization).toBe("Bearer ghp_token");
  });

  test("returns null on HTTP error", async () => {
    global.fetch.mockResolvedValueOnce(jsonRes(undefined, false));
    expect(await fetchWorkflowRuns("tok")).toBeNull();
  });

  test("returns null on network error", async () => {
    global.fetch.mockRejectedValueOnce(new Error("down"));
    expect(await fetchWorkflowRuns("tok")).toBeNull();
  });

  test("works without a token (public read path)", async () => {
    global.fetch.mockResolvedValueOnce(jsonRes({ workflow_runs: [{ id: 1 }] }));
    const got = await fetchWorkflowRuns(null);
    expect(got).toEqual([{ id: 1 }]);
    const opts = global.fetch.mock.calls[0][1];
    expect(opts.headers).toBeUndefined();
  });
});

describe("validateToken", () => {
  test("true when API accepts the token", async () => {
    global.fetch.mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve({}) });
    expect(await validateToken("ghp_ok")).toBe(true);
  });

  test("false on 401", async () => {
    global.fetch.mockResolvedValueOnce({ ok: false, status: 401, json: () => Promise.resolve({}) });
    expect(await validateToken("bad")).toBe(false);
  });

  test("false on network error", async () => {
    global.fetch.mockRejectedValueOnce(new Error("offline"));
    expect(await validateToken("tok")).toBe(false);
  });
});

describe("fetchTrace", () => {
  test("returns the trace array from the data branch", async () => {
    const trace = [
      { timestamp: "2026-08-15T10:00:00Z", risk_score: 0.1 },
      { timestamp: "2026-08-15T10:05:00Z", risk_score: 0.2 },
    ];
    global.fetch.mockResolvedValueOnce(jsonRes(trace));
    expect(await fetchTrace()).toEqual(trace);
  });

  test("falls back to mock trace on HTTP error", async () => {
    global.fetch.mockResolvedValueOnce(jsonRes(undefined, false));
    const trace = await fetchTrace();
    expect(Array.isArray(trace)).toBe(true);
    expect(trace.length).toBeGreaterThan(0);
    expect(trace[0].timestamp).toBeTruthy();
  });

  test("falls back to mock trace on network error", async () => {
    global.fetch.mockRejectedValueOnce(new Error("down"));
    const trace = await fetchTrace();
    expect(Array.isArray(trace)).toBe(true);
    expect(trace.length).toBeGreaterThan(0);
  });

  test("falls back to mock trace on empty or malformed body", async () => {
    global.fetch.mockResolvedValueOnce(jsonRes([]));
    expect((await fetchTrace()).length).toBeGreaterThan(0);
    global.fetch.mockResolvedValueOnce(jsonRes({ not: "an array" }));
    expect((await fetchTrace()).length).toBeGreaterThan(0);
    global.fetch.mockResolvedValueOnce(jsonRes("garbage"));
    expect((await fetchTrace()).length).toBeGreaterThan(0);
  });
});
