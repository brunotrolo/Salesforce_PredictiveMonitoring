/**
 * Dashboard utility functions for Salesforce Predictive Monitoring.
 */

export function getRiskLevel(riskScore) {
  if (riskScore >= 0.7) return "CRITICAL";
  if (riskScore >= 0.4) return "WARNING";
  return "HEALTHY";
}

export function getRiskColor(riskScore) {
  const level = getRiskLevel(riskScore);
  const colors = {
    CRITICAL: "#dc2626",
    WARNING: "#f59e0b",
    HEALTHY: "#22c55e",
  };
  return colors[level];
}

export function formatTimestamp(isoString) {
  const date = new Date(isoString);
  return date.toLocaleString("pt-BR", {
    timeZone: "America/Sao_Paulo",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function filterAlertsBySeverity(alerts, severity) {
  return alerts.filter((a) => a.severity === severity);
}

export function getAlertCounts(alerts) {
  return {
    CRITICAL: filterAlertsBySeverity(alerts, "CRITICAL").length,
    WARNING: filterAlertsBySeverity(alerts, "WARNING").length,
    total: alerts.length,
  };
}

export function getRecurringCount(aggregated) {
  return Array.isArray(aggregated)
    ? aggregated.filter((a) => a.recurring).length
    : 0;
}

export function summarizeAggregated(aggregated) {
  const list = Array.isArray(aggregated) ? aggregated : [];
  const counts = {
    CRITICAL: list.filter((a) => a.severity === "CRITICAL").length,
    WARNING: list.filter((a) => a.severity === "WARNING").length,
    INFO: list.filter((a) => a.severity === "INFO").length,
    total: list.length,
  };
  return {
    counts,
    recurring: getRecurringCount(list),
    totalOccurrences: list.reduce((sum, a) => sum + (a.count || 1), 0),
  };
}

export function getShadowVerdict(shadow) {
  if (!shadow || shadow.enabled !== true) return "INDISPONÍVEL";
  return shadow.verdict === "AGREE" ? "CONCORDA" : "DIVERGE";
}

export function summarizeShadow(shadow) {
  if (!shadow || shadow.enabled !== true) {
    return {
      enabled: false,
      verdict: getShadowVerdict(shadow),
      mlRisk: null,
      anomalies: 0,
      predicted: [],
    };
  }
  return {
    enabled: true,
    verdict: getShadowVerdict(shadow),
    mlRisk: Number(shadow.ml_risk ?? 0),
    anomalies: Number(shadow.anomalies?.count ?? 0),
    predicted: Array.isArray(shadow.forecast?.predicted)
      ? shadow.forecast.predicted.map(Number)
      : [],
  };
}

export function directionLabel(direction) {
  if (direction === "up") return "subindo";
  if (direction === "down") return "caindo";
  if (direction === "flat") return "estável";
  return direction ?? "desconhecida";
}

export function getAccuracyVerdict(accuracy) {
  if (!accuracy || accuracy.status !== "evaluated") return "SEM DADOS";
  if (accuracy.forecast_hit === true) return "ACERTOU";
  if (accuracy.forecast_hit === false) return "ERROU";
  return "INDETERMINADO";
}

export function summarizeAccuracy(accuracy) {
  if (!accuracy || accuracy.status !== "evaluated") {
    return {
      available: false,
      verdict: getAccuracyVerdict(accuracy),
      directionExpected: null,
      directionActual: null,
      forecastHit: null,
      anomalyFlagged: false,
      anomalyHit: null,
      falsePositive: false,
    };
  }
  return {
    available: true,
    verdict: getAccuracyVerdict(accuracy),
    directionExpected: accuracy.direction_expected ?? null,
    directionActual: accuracy.direction_actual ?? null,
    forecastHit: accuracy.forecast_hit ?? null,
    anomalyFlagged: Boolean(accuracy.anomaly_flagged),
    anomalyHit: accuracy.anomaly_hit ?? null,
    falsePositive: Boolean(accuracy.false_positive),
  };
}

export function summarizePipeline(pipeline) {
  if (!pipeline || typeof pipeline !== "object") {
    return {
      available: false,
      durationMs: null,
      steps: [],
      stepErrors: [],
      hasErrors: false,
    };
  }
  const steps = Array.isArray(pipeline.steps) ? pipeline.steps : [];
  const stepErrors = Array.isArray(pipeline.step_errors)
    ? pipeline.step_errors
    : [];
  return {
    available: true,
    durationMs:
      typeof pipeline.duration_ms === "number" ? pipeline.duration_ms : null,
    steps,
    stepErrors,
    hasErrors: stepErrors.length > 0,
  };
}

/**
 * Detect whether a raw log/alert message signals a circuit breaker
 * (Salesforce integration patterns): explicit breaker events, HTTP 429/503,
 * rate limiting and timeouts. Case-insensitive.
 */
export function isCircuitBreakerMessage(message) {
  const m = String(message || "").toLowerCase();
  return /circuit[\s_-]?breaker|breaker open|429|503|rate limit|too many requests|timeout/.test(m);
}

/**
 * Summarize the raw logs embedded in the latest snapshot.
 * Returns { total, errors, retried, circuitBreaker } — counts only; the
 * table itself is rendered directly from the raw rows in app.js.
 */
export function summarizeLogs(logs) {
  const list = Array.isArray(logs) ? logs : [];
  let errors = 0;
  let retried = 0;
  let circuitBreaker = 0;
  for (const log of list) {
    if (Number(log?.status_code ?? 0) >= 500) errors += 1;
    if (Boolean(log?.retried)) retried += 1;
    if (isCircuitBreakerMessage(log?.message)) circuitBreaker += 1;
  }
  return { total: list.length, errors, retried, circuitBreaker };
}

/**
 * Gap (in minutes) between two consecutive trace entries beyond which the
 * scheduler is considered to have skipped a cycle ("sem coleta").
 */
export const TRACE_GAP_MIN = 15;

/**
 * Risk level threshold for a "queda" (down window): two or more consecutive
 * cycles at or above this risk.
 */
export const TRACE_DOWN_RISK = 0.7;

/**
 * Summarize the rolling 24h trace for the health section.
 * Returns:
 *   - cycles: total entries
 *   - maxRisk: highest risk_score across the window
 *   - gaps: [{from, to, minutes, entry}] for every interval > TRACE_GAP_MIN
 *   - downWindows: [{from, to, peak, entry, entries}] for runs of >= 2
 *     consecutive entries with risk >= TRACE_DOWN_RISK (entry = the cycle
 *     with peak risk, entries = every cycle of the run)
 *   - anomalies: [{timestamp, entry}] for entries with anomalies > 0
 *   - breakers: [{timestamp, entry}] for entries with circuit_breaker true
 * Each event carries the source trace entry so the UI can link back to the
 * snapshot that produced it (full traceability).
 * Input is sorted by timestamp; a non-array input yields an empty summary.
 */
export function summarizeTrace(trace) {
  const list = Array.isArray(trace)
    ? trace.slice().sort((a, b) => String(a?.timestamp ?? "").localeCompare(String(b?.timestamp ?? "")))
    : [];
  const summary = {
    cycles: 0,
    maxRisk: 0,
    gaps: [],
    downWindows: [],
    anomalies: [],
    breakers: [],
  };
  if (list.length === 0) return summary;

  summary.cycles = list.length;
  summary.maxRisk = Math.max(
    0,
    ...list.map((entry) => Number(entry?.risk_score ?? 0))
  );

  for (let i = 1; i < list.length; i += 1) {
    const from = new Date(list[i - 1].timestamp);
    const to = new Date(list[i].timestamp);
    const minutes = (to.getTime() - from.getTime()) / 60000;
    if (Number.isFinite(minutes) && minutes > TRACE_GAP_MIN) {
      summary.gaps.push({
        from: list[i - 1].timestamp,
        to: list[i].timestamp,
        minutes: Math.round(minutes),
        entry: list[i],
      });
    }
  }

  let runStart = null;
  let runPeak = 0;
  let runPeakEntry = null;
  let runEntries = [];
  for (const entry of list) {
    const risk = Number(entry?.risk_score ?? 0);
    if (risk >= TRACE_DOWN_RISK) {
      if (runStart === null) runStart = entry.timestamp;
      if (risk > runPeak) {
        runPeak = risk;
        runPeakEntry = entry;
      }
      runEntries.push(entry);
    } else if (runStart !== null) {
      summary.downWindows.push({
        from: runStart,
        to: entry.timestamp,
        peak: runPeak,
        entry: runPeakEntry,
        entries: runEntries,
      });
      runStart = null;
      runPeak = 0;
      runPeakEntry = null;
      runEntries = [];
    }
    if (Number(entry?.anomalies ?? 0) > 0) {
      summary.anomalies.push({ timestamp: entry.timestamp, entry });
    }
    if (Boolean(entry?.circuit_breaker)) {
      summary.breakers.push({ timestamp: entry.timestamp, entry });
    }
  }
  if (runStart !== null) {
    summary.downWindows.push({
      from: runStart,
      to: list[list.length - 1].timestamp,
      peak: runPeak,
      entry: runPeakEntry,
      entries: runEntries,
    });
  }
  return summary;
}

/**
 * True when the latest snapshot is older than the given age in minutes —
 * drives the red "dados atrasados" banner. Never stale in mock mode.
 */
export function isStale(snapshot, maxAgeMinutes = 15) {
  if (!snapshot || !snapshot.timestamp) return false;
  if (snapshot.mode === "mock") return false;
  const ageMs = Date.now() - new Date(snapshot.timestamp).getTime();
  if (!Number.isFinite(ageMs) || ageMs < 0) return false;
  return ageMs / 60000 > maxAgeMinutes;
}
