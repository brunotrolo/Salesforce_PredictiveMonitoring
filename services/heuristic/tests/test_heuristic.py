"""Tests for Heuristic Engine service."""
from src.heuristic import HeuristicEngine


class TestHeuristicAnalyze:
    def test_analyze_mixed_logs(self, engine, mixed_logs):
        result = engine.analyze(mixed_logs)
        assert result["risk_score"] > 0
        assert result["risk_score"] <= 1
        assert len(result["alerts"]) >= 1

    def test_analyze_healthy_logs(self, engine, healthy_logs):
        result = engine.analyze(healthy_logs)
        assert result["risk_score"] == 0
        assert len(result["alerts"]) == 0
        assert result["errors_count"] == 0
        assert result["slow_count"] == 0

    def test_analyze_critical_logs(self, engine, critical_logs):
        result = engine.analyze(critical_logs)
        assert result["risk_score"] > 0
        assert result["risk_score"] <= 1.0
        assert result["errors_count"] == 2
        assert len(result["alerts"]) == 4  # 2 errors + 2 slow

    def test_analyze_empty_logs(self, engine):
        result = engine.analyze([])
        assert result["risk_score"] == 0
        assert result["alerts"] == []

    def test_risk_score_never_exceeds_one(self, engine):
        massive_errors = [
            {"log_id": f"L{i}", "status_code": 500, "duration_ms": 5000, "resource": f"/r{i}"}
            for i in range(100)
        ]
        result = engine.analyze(massive_errors)
        assert result["risk_score"] <= 1.0


class TestAlertSeverity:
    def test_error_creates_critical_alert(self, engine, critical_logs):
        result = engine.analyze(critical_logs)
        critical_alerts = [a for a in result["alerts"] if a["severity"] == "CRITICAL"]
        assert len(critical_alerts) == 2

    def test_slow_creates_warning(self, engine):
        slow_logs = [
            {"log_id": "L1", "status_code": 200, "duration_ms": 5000, "resource": "/api/slow"},
        ]
        result = engine.analyze(slow_logs)
        assert len(result["alerts"]) == 1
        assert result["alerts"][0]["severity"] == "WARNING"
