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
