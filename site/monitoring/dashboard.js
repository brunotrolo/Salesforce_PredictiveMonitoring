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
