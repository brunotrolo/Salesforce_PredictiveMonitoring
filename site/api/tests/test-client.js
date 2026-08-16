import { jest } from "@jest/globals";
import {
  fetchLatestSnapshot,
  fetchDay,
  fetchRecentSnapshots,
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