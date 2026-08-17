/**
 * GENERATED MIRROR — do not edit by hand.
 * Source: site/monitoring/mock-data.js
 * Regenerate: node site/scripts/sync-dashboard.mjs
 */

export const mockMonitoringData = {
  risk_score: 0.42,
  alerts: [
    { id: "A1", severity: "CRITICAL", message: "High error rate", timestamp: "2026-08-15T10:05:00Z" },
    { id: "A2", severity: "WARNING", message: "Slow response", timestamp: "2026-08-15T10:03:00Z" },
  ],
  health_check: {
    status: "HEALTHY",
    last_updated: "2026-08-15T10:05:00Z",
  },
  errors_count: 1,
  slow_requests_count: 1,
  shadow_mode: {
    enabled: true,
    heuristic_risk: 0.42,
    ml_risk: 0.4,
    agreement: 0.05,
    verdict: "AGREE",
    forecast: { predicted: [1, 1, 1] },
    anomalies: { count: 0 },
    series: [1, 1, 1],
  },
  accuracy: {
    status: "evaluated",
    direction_expected: "up",
    direction_actual: "up",
    forecast_hit: true,
    anomaly_flagged: true,
    anomaly_hit: true,
    false_positive: false,
    series_actual: [2, 4, 6],
  },
};

export const mockEmptyData = {
  risk_score: 0,
  alerts: [],
  health_check: {
    status: "HEALTHY",
    last_updated: "2026-08-15T10:00:00Z",
  },
  errors_count: 0,
  slow_requests_count: 0,
};

export const mockCriticalData = {
  risk_score: 0.95,
  alerts: [
    { id: "A1", severity: "CRITICAL", message: "Multiple failures", timestamp: "2026-08-15T10:10:00Z" },
    { id: "A2", severity: "CRITICAL", message: "Timeout cascade", timestamp: "2026-08-15T10:09:00Z" },
    { id: "A3", severity: "CRITICAL", message: "DB connection lost", timestamp: "2026-08-15T10:08:00Z" },
  ],
  health_check: {
    status: "CRITICAL",
    last_updated: "2026-08-15T10:10:00Z",
  },
  errors_count: 15,
  slow_requests_count: 8,
  shadow_mode: {
    enabled: true,
    heuristic_risk: 0.95,
    ml_risk: 0.9,
    agreement: 0.05,
    verdict: "AGREE",
    forecast: { predicted: [12, 14, 16] },
    anomalies: { count: 3 },
    series: [1, 2, 8, 10, 12],
  },
  accuracy: {
    status: "evaluated",
    direction_expected: "up",
    direction_actual: "flat",
    forecast_hit: false,
    anomaly_flagged: true,
    anomaly_hit: false,
    false_positive: true,
    series_actual: [3, 3, 3],
  },
};
