from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ComparisonResult(BaseModel):
    prediction: str
    confidence: float
    risk_delta: float
    summary: str


class ComparisonService:
    """Compares current heuristic analysis against historical baselines."""

    CRITICAL_INCREASE_THRESHOLD = 0.3
    MODERATE_INCREASE_THRESHOLD = 0.1
    CRITICAL_CONFIDENCE = 0.9
    MODERATE_CONFIDENCE = 0.7
    IMPROVEMENT_CONFIDENCE = 0.8
    STABLE_CONFIDENCE = 0.95

    def compare(
        self,
        current: dict[str, Any],
        historical: dict[str, Any] | None = None,
    ) -> ComparisonResult:
        """Compare current state to historical baseline."""
        if historical is None:
            historical = {"risk_score": 0.0, "errors_count": 0, "slow_count": 0}

        current_risk = current.get("risk_score", 0)
        hist_risk = historical.get("risk_score", 0)
        risk_delta = round(current_risk - hist_risk, 4)

        if risk_delta > self.CRITICAL_INCREASE_THRESHOLD:
            prediction = "CRITICAL_INCREASE"
            confidence = self.CRITICAL_CONFIDENCE
        elif risk_delta > self.MODERATE_INCREASE_THRESHOLD:
            prediction = "MODERATE_INCREASE"
            confidence = self.MODERATE_CONFIDENCE
        elif risk_delta < -self.MODERATE_INCREASE_THRESHOLD:
            prediction = "IMPROVEMENT"
            confidence = self.IMPROVEMENT_CONFIDENCE
        else:
            prediction = "STABLE"
            confidence = self.STABLE_CONFIDENCE

        return ComparisonResult(
            prediction=prediction,
            confidence=confidence,
            risk_delta=risk_delta,
            summary=f"Risk changed by {risk_delta:+.4f} ({prediction})",
        )
