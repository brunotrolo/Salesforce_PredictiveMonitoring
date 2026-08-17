"""Tests for the alerting service (aggregation and deduplication)."""

from alerting import AlertAggregator


class TestKeyFor:
    def test_key_normalizes_severity_kind_resource(self, service):
        alert = {
            "severity": "critical",
            "kind": "error",
            "resource": "/api/users",
        }
        assert service.key_for(alert) == "CRITICAL|ERROR|/API/USERS"

    def test_key_falls_back_to_resource_as_kind(self, service):
        alert = {"severity": "WARNING", "resource": "/api/x"}
        assert service.key_for(alert) == "WARNING|/API/X|/API/X"


class TestAggregate:
    def test_deduplicates_identical_alerts_with_count(self, service, sample_alerts):
        result = service.aggregate(sample_alerts)
        assert len(result) == 2
        critical = next(a for a in result if a.severity == "CRITICAL")
        assert critical.count == 2
        assert critical.log_ids == ["L1", "L2"]
        assert critical.first_seen == "2026-08-16T12:00:00Z"
        assert critical.last_seen == "2026-08-16T12:01:00Z"

    def test_orders_by_severity_then_count(self, service):
        alerts = [
            {
                "severity": "WARNING",
                "kind": "slow",
                "resource": "/api/a",
                "message": "m1",
            },
            {
                "severity": "CRITICAL",
                "kind": "error",
                "resource": "/api/b",
                "message": "m2",
            },
            {"severity": "INFO", "kind": "info", "resource": "/api/c", "message": "m3"},
        ]
        result = service.aggregate(alerts)
        severities = [a.severity for a in result]
        assert severities == ["CRITICAL", "WARNING", "INFO"]

    def test_empty_alerts(self, service):
        assert service.aggregate([]) == []

    def test_marks_recurring_from_history(self, service, sample_alerts):
        key = service.key_for(sample_alerts[0])
        result = service.aggregate(sample_alerts, history={key: 3})
        critical = next(a for a in result if a.severity == "CRITICAL")
        assert critical.recurring is True
        assert critical.repeat_count == 3

    def test_no_recurrence_without_history(self, service, sample_alerts):
        result = service.aggregate(sample_alerts)
        critical = next(a for a in result if a.severity == "CRITICAL")
        assert critical.recurring is False
        assert critical.repeat_count == 0

    def test_limits_log_ids_to_twenty(self, service):
        alerts = [
            {
                "severity": "WARNING",
                "kind": "slow",
                "resource": "/api/x",
                "message": "m",
                "log_id": f"L{i}",
            }
            for i in range(30)
        ]
        result = service.aggregate(alerts)
        assert len(result[0].log_ids) == 20


class TestSeverityCounts:
    def test_counts_by_severity(self, service, sample_alerts):
        result = service.aggregate(sample_alerts)
        counts = service.severity_counts(result)
        assert counts == {"INFO": 0, "WARNING": 1, "CRITICAL": 1}


class TestHistoryFromSnapshot:
    def test_extracts_from_aggregated(self, service):
        snapshot = {
            "alerts_aggregated": [
                {
                    "key": "CRITICAL|ERROR|/API/USERS",
                    "recurring": True,
                    "repeat_count": 2,
                },
                {"key": "WARNING|SLOW|/API/P", "recurring": False, "repeat_count": 0},
            ]
        }
        history = AlertAggregator.history_from_snapshot(snapshot)
        assert history == {
            "CRITICAL|ERROR|/API/USERS": 3,
            "WARNING|SLOW|/API/P": 1,
        }

    def test_extracts_from_raw_legacy_alerts(self, service):
        snapshot = {
            "alerts": [
                {"severity": "CRITICAL", "kind": "error", "resource": "/api/users"},
                {"severity": "CRITICAL", "kind": "error", "resource": "/api/users"},
                {"severity": "WARNING", "kind": "slow", "resource": "/api/products"},
            ]
        }
        history = AlertAggregator.history_from_snapshot(snapshot)
        assert history == {
            "CRITICAL|ERROR|/API/USERS": 2,
            "WARNING|SLOW|/API/PRODUCTS": 1,
        }

    def test_empty_snapshot(self, service):
        assert AlertAggregator.history_from_snapshot({}) == {}
