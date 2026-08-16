import { getRiskLevel, getRiskColor, formatTimestamp, filterAlertsBySeverity, getAlertCounts } from "../dashboard.js";
import { mockMonitoringData, mockEmptyData, mockCriticalData } from "../mock-data.js";

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
});
