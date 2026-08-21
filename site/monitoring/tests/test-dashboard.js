import { getRiskLevel, getRiskColor, formatTimestamp, filterAlertsBySeverity, getAlertCounts, getRecurringCount, summarizeAggregated, getShadowVerdict, summarizeShadow, directionLabel, getAccuracyVerdict, summarizeAccuracy, summarizePipeline, summarizeLogs, summarizeTrace, isStale, isCircuitBreakerMessage, summarizeComparison, summarizeHealthCheck, summarizeCalibration, summarizeFeedback } from "../dashboard.js";
import { mockMonitoringData, mockEmptyData, mockCriticalData, mockTraceData } from "../mock-data.js";

describe("Dashboard", () => {
  describe("mock data", () => {
    test("renders risk score", () => {
      const { risk_score } = mockMonitoringData;
      expect(risk_score).toBe(0.42);
    });

    test("displays alerts", () => {
      const { alerts } = mockMonitoringData;
      expect(alerts.length).toBe(2);
      expect(alerts[0].severity).toBe("CRITICAL");
    });

    test("shows health check status", () => {
      const { health_check } = mockMonitoringData;
      expect(health_check.status).toBe("HEALTHY");
    });
  });

  describe("getRiskLevel", () => {
    test("returns CRITICAL for high risk", () => {
      expect(getRiskLevel(0.95)).toBe("CRITICAL");
      expect(getRiskLevel(0.7)).toBe("CRITICAL");
    });

    test("returns WARNING for medium risk", () => {
      expect(getRiskLevel(0.4)).toBe("WARNING");
      expect(getRiskLevel(0.6)).toBe("WARNING");
    });

    test("returns HEALTHY for low risk", () => {
      expect(getRiskLevel(0)).toBe("HEALTHY");
      expect(getRiskLevel(0.3)).toBe("HEALTHY");
    });
  });

  describe("getRiskColor", () => {
    test("returns red for CRITICAL", () => {
      expect(getRiskColor(0.95)).toBe("#dc2626");
    });

    test("returns yellow for WARNING", () => {
      expect(getRiskColor(0.5)).toBe("#f59e0b");
    });

    test("returns green for HEALTHY", () => {
      expect(getRiskColor(0.1)).toBe("#22c55e");
    });
  });

  describe("formatTimestamp", () => {
    test("formats ISO timestamp", () => {
      const result = formatTimestamp("2026-08-15T10:05:00Z");
      expect(typeof result).toBe("string");
      expect(result.length).toBeGreaterThan(0);
    });
  });

  describe("filterAlertsBySeverity", () => {
    test("filters CRITICAL alerts", () => {
      const critical = filterAlertsBySeverity(mockMonitoringData.alerts, "CRITICAL");
      expect(critical.length).toBe(1);
      expect(critical[0].id).toBe("A1");
    });

    test("filters WARNING alerts", () => {
      const warnings = filterAlertsBySeverity(mockMonitoringData.alerts, "WARNING");
      expect(warnings.length).toBe(1);
    });

    test("returns empty for non-existent severity", () => {
      const none = filterAlertsBySeverity(mockMonitoringData.alerts, "INFO");
      expect(none.length).toBe(0);
    });
  });

  describe("getAlertCounts", () => {
    test("counts all alerts correctly", () => {
      const counts = getAlertCounts(mockMonitoringData.alerts);
      expect(counts.CRITICAL).toBe(1);
      expect(counts.WARNING).toBe(1);
      expect(counts.total).toBe(2);
    });

    test("returns zeros for empty alerts", () => {
      const counts = getAlertCounts(mockEmptyData.alerts);
      expect(counts.CRITICAL).toBe(0);
      expect(counts.WARNING).toBe(0);
      expect(counts.total).toBe(0);
    });
  });

  describe("getRecurringCount", () => {
    test("counts recurring aggregated alerts", () => {
      const aggregated = [
        { key: "A", recurring: true },
        { key: "B", recurring: false },
        { key: "C", recurring: true },
      ];
      expect(getRecurringCount(aggregated)).toBe(2);
    });

    test("returns zero for empty or missing", () => {
      expect(getRecurringCount([])).toBe(0);
      expect(getRecurringCount(undefined)).toBe(0);
    });
  });

  describe("summarizeAggregated", () => {
    const aggregated = [
      { severity: "CRITICAL", count: 3, recurring: true },
      { severity: "WARNING", count: 2, recurring: false },
      { severity: "WARNING", count: 1, recurring: true },
    ];

    test("computes counts by severity", () => {
      const { counts } = summarizeAggregated(aggregated);
      expect(counts.CRITICAL).toBe(1);
      expect(counts.WARNING).toBe(2);
      expect(counts.INFO).toBe(0);
      expect(counts.total).toBe(3);
    });

    test("sums occurrences and recurring", () => {
      const summary = summarizeAggregated(aggregated);
      expect(summary.totalOccurrences).toBe(6);
      expect(summary.recurring).toBe(2);
    });

    test("handles missing input", () => {
      const summary = summarizeAggregated(undefined);
      expect(summary.counts.total).toBe(0);
      expect(summary.totalOccurrences).toBe(0);
    });
  });

  describe("critical data", () => {
    test("critical data has high risk score", () => {
      expect(mockCriticalData.risk_score).toBeGreaterThanOrEqual(0.7);
    });

    test("critical data has CRITICAL health check", () => {
      expect(mockCriticalData.health_check.status).toBe("CRITICAL");
    });

    test("critical data has multiple critical alerts", () => {
      const critical = filterAlertsBySeverity(mockCriticalData.alerts, "CRITICAL");
      expect(critical.length).toBeGreaterThanOrEqual(3);
    });
  });

  describe("getShadowVerdict", () => {
    test("returns CONCORDA for AGREE", () => {
      expect(getShadowVerdict({ enabled: true, verdict: "AGREE" })).toBe("CONCORDA");
    });

    test("returns DIVERGE for DISAGREE", () => {
      expect(getShadowVerdict({ enabled: true, verdict: "DISAGREE" })).toBe("DIVERGE");
    });

    test("returns INDISPONÍVEL when disabled or missing", () => {
      expect(getShadowVerdict({ enabled: false })).toBe("INDISPONÍVEL");
      expect(getShadowVerdict(undefined)).toBe("INDISPONÍVEL");
      expect(getShadowVerdict({ enabled: true, verdict: null })).toBe("DIVERGE");
    });
  });

  describe("summarizeShadow", () => {
    test("summarizes an enabled shadow block", () => {
      const shadow = {
        enabled: true,
        ml_risk: 0.4,
        verdict: "AGREE",
        anomalies: { count: 2 },
        forecast: { predicted: [3, 2, 1] },
      };
      const summary = summarizeShadow(shadow);
      expect(summary.enabled).toBe(true);
      expect(summary.verdict).toBe("CONCORDA");
      expect(summary.mlRisk).toBe(0.4);
      expect(summary.anomalies).toBe(2);
      expect(summary.predicted).toEqual([3, 2, 1]);
    });

    test("treats missing numbers as zero", () => {
      const summary = summarizeShadow({ enabled: true, verdict: "AGREE" });
      expect(summary.mlRisk).toBe(0);
      expect(summary.anomalies).toBe(0);
      expect(summary.predicted).toEqual([]);
    });

    test("returns safe fallback when disabled", () => {
      const summary = summarizeShadow(undefined);
      expect(summary.enabled).toBe(false);
      expect(summary.verdict).toBe("INDISPONÍVEL");
      expect(summary.mlRisk).toBe(null);
      expect(summary.anomalies).toBe(0);
      expect(summary.predicted).toEqual([]);
    });
  });

  describe("directionLabel", () => {
    test("maps up/down/flat to Portuguese", () => {
      expect(directionLabel("up")).toBe("subindo");
      expect(directionLabel("down")).toBe("caindo");
      expect(directionLabel("flat")).toBe("estável");
    });

    test("falls back for unknown values", () => {
      expect(directionLabel(undefined)).toBe("desconhecida");
      expect(directionLabel("bogus")).toBe("bogus");
    });
  });

  describe("getAccuracyVerdict", () => {
    test("returns ACERTOU on forecast hit", () => {
      expect(getAccuracyVerdict({ status: "evaluated", forecast_hit: true })).toBe("ACERTOU");
    });

    test("returns ERROU on forecast miss", () => {
      expect(getAccuracyVerdict({ status: "evaluated", forecast_hit: false })).toBe("ERROU");
    });

    test("returns INDETERMINADO for flat direction", () => {
      expect(getAccuracyVerdict({ status: "evaluated", forecast_hit: null })).toBe("INDETERMINADO");
    });

    test("returns SEM DADOS when not evaluated", () => {
      expect(getAccuracyVerdict(undefined)).toBe("SEM DADOS");
      expect(getAccuracyVerdict({ status: "no_data" })).toBe("SEM DADOS");
    });
  });

  describe("summarizeAccuracy", () => {
    test("summarizes an evaluated accuracy block", () => {
      const summary = summarizeAccuracy({
        status: "evaluated",
        direction_expected: "up",
        direction_actual: "up",
        forecast_hit: true,
        anomaly_flagged: true,
        anomaly_hit: true,
        false_positive: false,
      });
      expect(summary.available).toBe(true);
      expect(summary.verdict).toBe("ACERTOU");
      expect(summary.directionExpected).toBe("up");
      expect(summary.directionActual).toBe("up");
      expect(summary.forecastHit).toBe(true);
      expect(summary.anomalyFlagged).toBe(true);
      expect(summary.anomalyHit).toBe(true);
      expect(summary.falsePositive).toBe(false);
    });

    test("coerces booleans on missing flags", () => {
      const summary = summarizeAccuracy({
        status: "evaluated",
        direction_expected: "down",
        direction_actual: "flat",
        forecast_hit: false,
      });
      expect(summary.anomalyFlagged).toBe(false);
      expect(summary.anomalyHit).toBe(null);
      expect(summary.falsePositive).toBe(false);
    });

    test("returns safe fallback when not evaluated", () => {
      const summary = summarizeAccuracy(undefined);
      expect(summary.available).toBe(false);
      expect(summary.verdict).toBe("SEM DADOS");
      expect(summary.directionExpected).toBe(null);
      expect(summary.anomalyFlagged).toBe(false);
    });
  });

  describe("summarizePipeline", () => {
    test("summarizes an enabled pipeline block", () => {
      const summary = summarizePipeline(mockMonitoringData.pipeline);
      expect(summary.available).toBe(true);
      expect(summary.durationMs).toBe(137);
      expect(summary.steps).toEqual([
        "collect",
        "analyze",
        "aggregate",
        "compare",
        "shadow",
      ]);
      expect(summary.stepErrors).toEqual([]);
      expect(summary.hasErrors).toBe(false);
    });

    test("flags step errors when present", () => {
      const summary = summarizePipeline(mockCriticalData.pipeline);
      expect(summary.hasErrors).toBe(true);
      expect(summary.stepErrors).toEqual([
        { step: "feedback", error: "FileNotFoundError: nope.json" },
      ]);
      expect(summary.durationMs).toBe(251);
    });

    test("returns safe fallback when missing", () => {
      const summary = summarizePipeline(undefined);
      expect(summary.available).toBe(false);
      expect(summary.durationMs).toBe(null);
      expect(summary.steps).toEqual([]);
      expect(summary.stepErrors).toEqual([]);
      expect(summary.hasErrors).toBe(false);
    });

    test("handles non-array fields defensively", () => {
      const summary = summarizePipeline({ duration_ms: 99 });
      expect(summary.steps).toEqual([]);
      expect(summary.stepErrors).toEqual([]);
      expect(summary.hasErrors).toBe(false);
    });

    test("treats non-numeric duration as null", () => {
      const summary = summarizePipeline({ duration_ms: "fast" });
      expect(summary.durationMs).toBe(null);
    });
  });

  describe("summarizeComparison", () => {
    test("summarizes an available comparison block", () => {
      const summary = summarizeComparison({
        prediction: "UP",
        confidence: 0.85,
        risk_delta: 0.12,
        summary: "Forecast up",
      });
      expect(summary.available).toBe(true);
      expect(summary.prediction).toBe("UP");
      expect(summary.predictionLabel).toBe("↑ Subir");
      expect(summary.confidence).toBe(85);
      expect(summary.riskDelta).toBe(0.12);
      expect(summary.summary).toBe("Forecast up");
    });

    test("maps DOWN and STABLE predictions", () => {
      expect(summarizeComparison({ prediction: "DOWN" }).predictionLabel).toBe("↓ Cair");
      expect(summarizeComparison({ prediction: "STABLE" }).predictionLabel).toBe("— Estável");
    });

    test("falls back for null/missing fields", () => {
      const summary = summarizeComparison({ prediction: null });
      expect(summary.available).toBe(true);
      expect(summary.predictionLabel).toBe("—");
      expect(summary.confidence).toBe(null);
      expect(summary.riskDelta).toBe(null);
    });

    test("returns safe fallback when undefined", () => {
      const summary = summarizeComparison(undefined);
      expect(summary.available).toBe(false);
      expect(summary.prediction).toBe(null);
      expect(summary.predictionLabel).toBe("—");
      expect(summary.confidence).toBe(null);
      expect(summary.riskDelta).toBe(null);
      expect(summary.summary).toBe("");
    });

    test("returns safe fallback for non-object input", () => {
      expect(summarizeComparison("nope").available).toBe(false);
      expect(summarizeComparison(42).available).toBe(false);
    });

    test("rounds non-number confidence to null", () => {
      expect(summarizeComparison({ confidence: "high" }).confidence).toBe(null);
    });
  });

  describe("summarizeHealthCheck", () => {
    test("summarizes a HEALTHY check", () => {
      const summary = summarizeHealthCheck({ status: "HEALTHY", last_updated: "2026-08-21" });
      expect(summary.available).toBe(true);
      expect(summary.status).toBe("HEALTHY");
      expect(summary.statusLabel).toBe("SAUDÁVEL");
      expect(summary.lastUpdated).toBe("2026-08-21");
    });

    test("summarizes a WARNING check", () => {
      expect(summarizeHealthCheck({ status: "WARNING" }).statusLabel).toBe("ATENÇÃO");
    });

    test("handles unknown status", () => {
      const summary = summarizeHealthCheck({ status: "DEGRADED" });
      expect(summary.status).toBe("DEGRADED");
      expect(summary.statusLabel).toBe("DEGRADED");
    });

    test("lowercases then uppercases input status", () => {
      const summary = summarizeHealthCheck({ status: "healthy" });
      expect(summary.status).toBe("HEALTHY");
    });

    test("returns safe fallback when undefined", () => {
      const summary = summarizeHealthCheck(undefined);
      expect(summary.available).toBe(false);
      expect(summary.status).toBe("UNKNOWN");
      expect(summary.statusLabel).toBe("—");
    });

    test("returns safe fallback for non-object input", () => {
      expect(summarizeHealthCheck(null).available).toBe(false);
      expect(summarizeHealthCheck("str").available).toBe(false);
    });
  });

  describe("summarizeCalibration", () => {
    test("summarizes an ACTIVE calibration", () => {
      const summary = summarizeCalibration({
        status: "ACTIVE",
        samples: 150,
        avg_fp_rate: 0.05,
        current_threshold: 0.7,
        recommended_threshold: 0.65,
      });
      expect(summary.available).toBe(true);
      expect(summary.status).toBe("ACTIVE");
      expect(summary.statusLabel).toBe("ATIVA");
      expect(summary.samples).toBe(150);
      expect(summary.avgFpRate).toBe(5);
      expect(summary.currentThreshold).toBe(0.7);
      expect(summary.recommendedThreshold).toBe(0.65);
    });

    test("summarizes WARMING_UP calibration", () => {
      expect(summarizeCalibration({ status: "warming_up" }).statusLabel).toBe("AQUECENDO");
    });

    test("summarizes INACTIVE calibration", () => {
      expect(summarizeCalibration({ status: "inactive" }).statusLabel).toBe("INATIVA");
    });

    test("handles unknown status", () => {
      expect(summarizeCalibration({ status: "UNKNOWN" }).statusLabel).toBe("UNKNOWN");
    });

    test("coerces non-number fields to null", () => {
      const summary = summarizeCalibration({
        status: "ACTIVE",
        samples: "many",
        avg_fp_rate: "low",
        current_threshold: "x",
        recommended_threshold: null,
      });
      expect(summary.samples).toBe(null);
      expect(summary.avgFpRate).toBe(null);
      expect(summary.currentThreshold).toBe(null);
      expect(summary.recommendedThreshold).toBe(null);
    });

    test("returns safe fallback when undefined", () => {
      const summary = summarizeCalibration(undefined);
      expect(summary.available).toBe(false);
      expect(summary.status).toBe(null);
      expect(summary.statusLabel).toBe("—");
      expect(summary.samples).toBe(null);
      expect(summary.avgFpRate).toBe(null);
      expect(summary.currentThreshold).toBe(null);
      expect(summary.recommendedThreshold).toBe(null);
    });
  });

  describe("summarizeFeedback", () => {
    test("summarizes an available feedback block", () => {
      const summary = summarizeFeedback({
        loaded: 10,
        valid: 8,
        invalid: 2,
        by_action: { "set_price": 5, "update_stock": 3 },
        by_target: { "ML": 7, "SHOPEE": 1 },
      });
      expect(summary.available).toBe(true);
      expect(summary.loaded).toBe(10);
      expect(summary.valid).toBe(8);
      expect(summary.invalid).toBe(2);
      expect(summary.byAction).toEqual({ "set_price": 5, "update_stock": 3 });
      expect(summary.byTarget).toEqual({ "ML": 7, "SHOPEE": 1 });
    });

    test("defaults missing fields to zero/empty", () => {
      const summary = summarizeFeedback({});
      expect(summary.available).toBe(true);
      expect(summary.loaded).toBe(0);
      expect(summary.valid).toBe(0);
      expect(summary.invalid).toBe(0);
      expect(summary.byAction).toEqual({});
      expect(summary.byTarget).toEqual({});
    });

    test("returns safe fallback when undefined", () => {
      const summary = summarizeFeedback(undefined);
      expect(summary.available).toBe(false);
      expect(summary.loaded).toBe(0);
      expect(summary.valid).toBe(0);
      expect(summary.invalid).toBe(0);
      expect(summary.byAction).toEqual({});
      expect(summary.byTarget).toEqual({});
    });

    test("returns safe fallback for non-object input", () => {
      expect(summarizeFeedback(null).available).toBe(false);
      expect(summarizeFeedback("str").available).toBe(false);
      expect(summarizeFeedback(42).available).toBe(false);
    });
  });
});

describe("summarizeLogs", () => {
  test("counts errors, retries and circuit breaker hits", () => {
    const summary = summarizeLogs(mockMonitoringData.logs);
    expect(summary.total).toBe(3);
    expect(summary.errors).toBe(1);
    expect(summary.retried).toBe(1);
    expect(summary.circuitBreaker).toBe(1);
  });

  test("returns zeroes for missing or non-array logs", () => {
    expect(summarizeLogs(undefined)).toEqual({ total: 0, errors: 0, retried: 0, circuitBreaker: 0 });
    expect(summarizeLogs("nope")).toEqual({ total: 0, errors: 0, retried: 0, circuitBreaker: 0 });
    expect(summarizeLogs([])).toEqual({ total: 0, errors: 0, retried: 0, circuitBreaker: 0 });
  });

  test("flags only real 5xx as errors", () => {
    const summary = summarizeLogs([
      { status_code: 500, retried: false, message: "boom" },
      { status_code: 200, retried: true, message: "ok" },
      { status_code: 404, retried: false, message: "not found" },
    ]);
    expect(summary.errors).toBe(1);
    expect(summary.retried).toBe(1);
  });
});

describe("isCircuitBreakerMessage", () => {
  test("detects breaker, 429/503, rate limit and timeout", () => {
    expect(isCircuitBreakerMessage("Circuit breaker opened")).toBe(true);
    expect(isCircuitBreakerMessage("HTTP 503 from OrgApi")).toBe(true);
    expect(isCircuitBreakerMessage("rate limit exceeded")).toBe(true);
    expect(isCircuitBreakerMessage("timeout on query")).toBe(true);
    expect(isCircuitBreakerMessage("All good here")).toBe(false);
    expect(isCircuitBreakerMessage(undefined)).toBe(false);
    expect(isCircuitBreakerMessage("429")).toBe(true);
  });
});

describe("summarizeTrace", () => {
  test("summarizes the mock trace", () => {
    const summary = summarizeTrace(mockTraceData);
    expect(summary.cycles).toBe(9);
    expect(summary.gaps.length).toBeGreaterThan(0);
    expect(summary.downWindows.length).toBe(1);
    expect(summary.breakers.length).toBe(2);
    expect(summary.anomalies.length).toBeGreaterThan(0);
    expect(summary.maxRisk).toBeGreaterThanOrEqual(0.9);
  });

  test("detects the 2h gap in the mock trace", () => {
    const summary = summarizeTrace(mockTraceData);
    const biggest = summary.gaps.reduce((a, b) => (b.minutes > a.minutes ? b : a), summary.gaps[0]);
    expect(biggest.minutes).toBeGreaterThanOrEqual(120);
  });

  test("returns empty summary for missing/empty/non-array", () => {
    expect(summarizeTrace(undefined)).toEqual({ cycles: 0, maxRisk: 0, gaps: [], downWindows: [], anomalies: [], breakers: [] });
    expect(summarizeTrace([])).toEqual({ cycles: 0, maxRisk: 0, gaps: [], downWindows: [], anomalies: [], breakers: [] });
    expect(summarizeTrace("nope")).toEqual({ cycles: 0, maxRisk: 0, gaps: [], downWindows: [], anomalies: [], breakers: [] });
  });

  test("sorts input by timestamp", () => {
    const summary = summarizeTrace([
      { timestamp: "2026-08-15T10:05:00Z", risk_score: 0.2 },
      { timestamp: "2026-08-15T10:00:00Z", risk_score: 0.1 },
    ]);
    expect(summary.cycles).toBe(2);
    expect(summary.gaps).toEqual([]);
    expect(summary.maxRisk).toBe(0.2);
  });

  test("does not flag intervals at the gap threshold", () => {
    const entries = [];
    for (let i = 0; i < 4; i += 1) {
      entries.push({ timestamp: `2026-08-15T10:0${i}:00Z`, risk_score: 0.1 });
    }
    expect(summarizeTrace(entries).gaps).toEqual([]);
  });

  test("only flags consecutive critical runs as down windows", () => {
const summary = summarizeTrace([
      { timestamp: "2026-08-15T10:00:00Z", risk_score: 0.8 },
      { timestamp: "2026-08-15T10:05:00Z", risk_score: 0.9 },
      { timestamp: "2026-08-15T10:10:00Z", risk_score: 0.2 },
      { timestamp: "2026-08-15T10:15:00Z", risk_score: 0.65 },
      { timestamp: "2026-08-15T10:20:00Z", risk_score: 0.3 },
    ]);
expect(summary.downWindows).toHaveLength(1);
    expect(summary.downWindows[0].peak).toBe(0.9);
  });

  test("carries the source entry and snapshot link on every event", () => {
    const raw =
      "https://raw.githubusercontent.com/brunotrolo/Salesforce_PredictiveMonitoring/data/2026-08-15/2026-08-15T10-05-00Z.json";
    const summary = summarizeTrace([
      { timestamp: "2026-08-15T09:00:00Z", risk_score: 0.1 },
      { timestamp: "2026-08-15T10:05:00Z", risk_score: 0.9, snapshot_raw: raw, evidence: { error_endpoints: [{ resource: "/api/products", count: 3 }], alerts: [] }, circuit_breaker: true, breaker_messages: ["rate limit"], anomalies: 4 },
    ]);
    expect(summary.gaps).toHaveLength(1);
    expect(summary.gaps[0].entry.snapshot_raw).toBe(raw);
    expect(summary.downWindows[0].entry.snapshot_raw).toBe(raw);
    expect(summary.downWindows[0].entries.map((e) => e.risk_score)).toEqual([0.9]);
    expect(summary.anomalies[0]).toEqual({ timestamp: "2026-08-15T10:05:00Z", entry: expect.objectContaining({ snapshot_raw: raw }) });
    expect(summary.breakers[0].entry.breaker_messages).toEqual(["rate limit"]);
  });

  test("empty summary keeps the exact lean shape", () => {
    expect(summarizeTrace([])).toEqual({ cycles: 0, maxRisk: 0, gaps: [], downWindows: [], anomalies: [], breakers: [] });
  });
});

describe("isStale", () => {
  const fresh = { timestamp: new Date().toISOString(), mode: "real" };
  const old = { timestamp: new Date(Date.now() - 60 * 60 * 1000).toISOString(), mode: "real" };

  test("flags snapshots older than the threshold", () => {
    expect(isStale(old)).toBe(true);
    expect(isStale(fresh)).toBe(false);
  });

  test("never flags mock mode", () => {
    expect(isStale({ ...old, mode: "mock" })).toBe(false);
  });

  test("safe fallback for missing data", () => {
    expect(isStale(null)).toBe(false);
    expect(isStale({})).toBe(false);
  });
});
