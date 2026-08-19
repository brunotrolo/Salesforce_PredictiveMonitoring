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
  pipeline: {
    duration_ms: 137,
    steps: ["collect", "analyze", "aggregate", "compare", "shadow"],
    step_errors: [],
  },
  logs: [
    {
      log_id: "log-mock-1",
      timestamp: "2026-08-15T10:05:00Z",
      status_code: 500,
      duration_ms: 900,
      resource: "OrgApi/query",
      severity: "ERROR",
      message: "Circuit breaker opened after 12 retries on OrgApi/query",
      retried: true,
    },
    {
      log_id: "log-mock-2",
      timestamp: "2026-08-15T10:04:57Z",
      status_code: 200,
      duration_ms: 120,
      resource: "OrgApi/describe",
      severity: "INFO",
      message: "SObject describe OK",
      retried: false,
    },
    {
      log_id: "log-mock-3",
      timestamp: "2026-08-15T10:04:40Z",
      status_code: 200,
      duration_ms: 1500,
      resource: "OrgApi/query",
      severity: "WARNING",
      message: "Slow response (1500ms) on OrgApi/query",
      retried: false,
    },
  ],
};

export const mockTraceData = [
  { timestamp: "2026-08-14T10:00:00Z", risk_score: 0.12, errors_count: 0, retried_count: 0, alerts_critical: 0, alerts_warning: 0, ml_risk: 0.1, anomalies: 0, circuit_breaker: false },
  { timestamp: "2026-08-14T10:05:00Z", risk_score: 0.2, errors_count: 1, retried_count: 0, alerts_critical: 0, alerts_warning: 1, ml_risk: 0.18, anomalies: 0, circuit_breaker: false },
  { timestamp: "2026-08-14T12:30:00Z", risk_score: 0.85, errors_count: 14, retried_count: 6, alerts_critical: 3, alerts_warning: 2, ml_risk: 0.9, anomalies: 2, circuit_breaker: true },
  { timestamp: "2026-08-14T12:35:00Z", risk_score: 0.92, errors_count: 18, retried_count: 8, alerts_critical: 4, alerts_warning: 1, ml_risk: 0.95, anomalies: 3, circuit_breaker: true },
  { timestamp: "2026-08-14T12:40:00Z", risk_score: 0.45, errors_count: 5, retried_count: 2, alerts_critical: 1, alerts_warning: 1, ml_risk: 0.5, anomalies: 1, circuit_breaker: false },
  { timestamp: "2026-08-14T18:00:00Z", risk_score: 0.31, errors_count: 2, retried_count: 1, alerts_critical: 0, alerts_warning: 2, ml_risk: 0.28, anomalies: 0, circuit_breaker: false },
  { timestamp: "2026-08-14T18:05:00Z", risk_score: 0.08, errors_count: 0, retried_count: 0, alerts_critical: 0, alerts_warning: 0, ml_risk: 0.09, anomalies: 0, circuit_breaker: false },
  { timestamp: "2026-08-15T08:00:00Z", risk_score: 0.5, errors_count: 6, retried_count: 1, alerts_critical: 1, alerts_warning: 2, ml_risk: 0.46, anomalies: 0, circuit_breaker: false },
  { timestamp: "2026-08-15T08:05:00Z", risk_score: 0.38, errors_count: 3, retried_count: 0, alerts_critical: 0, alerts_warning: 2, ml_risk: 0.34, anomalies: 0, circuit_breaker: false },
];

export const mockEmptyData = {
  risk_score: 0,
  alerts: [],
  health_check: {
    status: "HEALTHY",
    last_updated: "2026-08-15T10:00:00Z",
  },
  errors_count: 0,
  slow_requests_count: 0,
  logs: [],
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
  pipeline: {
    duration_ms: 251,
    steps: [
      "collect",
      "analyze",
      "aggregate",
      "compare",
      "shadow",
      "accuracy",
      "feedback",
    ],
    step_errors: [{ step: "feedback", error: "FileNotFoundError: nope.json" }],
  },
};
