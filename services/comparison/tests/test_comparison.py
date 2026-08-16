"""Tests for Comparison service."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.comparison import ComparisonService


class TestComparisonService:
    def test_critical_increase(self, service, current_high_risk, historical_baseline):
        result = service.compare(current_high_risk, historical_baseline)
        assert result.prediction == "CRITICAL_INCREASE"
        assert result.confidence == 0.9
        assert result.risk_delta > 0

    def test_stable(self, service):
        current = {"risk_score": 0.2, "errors_count": 1, "slow_count": 1}
        historical = {"risk_score": 0.2, "errors_count": 1, "slow_count": 1}
        result = service.compare(current, historical)
        assert result.prediction == "STABLE"
        assert result.confidence == 0.95

    def test_improvement(self, service):
        current = {"risk_score": 0.1, "errors_count": 0, "slow_count": 0}
        historical = {"risk_score": 0.5, "errors_count": 3, "slow_count": 2}
        result = service.compare(current, historical)
        assert result.prediction == "IMPROVEMENT"
        assert result.risk_delta < 0

    def test_compare_without_historical(self, service, current_high_risk):
        result = service.compare(current_high_risk)
        assert result.risk_delta == 0.8
        assert result.prediction == "CRITICAL_INCREASE"

    def test_moderate_increase(self, service):
        current = {"risk_score": 0.3}
        historical = {"risk_score": 0.15}
        result = service.compare(current, historical)
        assert result.prediction == "MODERATE_INCREASE"
        assert result.confidence == 0.7
