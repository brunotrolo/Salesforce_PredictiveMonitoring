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

        if risk_delta > 0.3:
            prediction = "CRITICAL_INCREASE"
            confidence = 0.9
        elif risk_delta > 0.1:
            prediction = "MODERATE_INCREASE"
            confidence = 0.7
        elif risk_delta < -0.1:
            prediction = "IMPROVEMENT"
            confidence = 0.8
        else:
            prediction = "STABLE"
            confidence = 0.95

        return ComparisonResult(
            prediction=prediction,
            confidence=confidence,
            risk_delta=risk_delta,
            summary=f"Risk changed by {risk_delta:+.4f} ({prediction})",
        )
