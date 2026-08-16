from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class Alert(BaseModel):
    severity: str
    message: str
    log_id: str = ""
    timestamp: str = ""


class HeuristicEngine:
    """Applies rule-based heuristics to analyze Salesforce logs."""

    ERROR_STATUS_THRESHOLD = 500
    SLOW_DURATION_THRESHOLD_MS = 1000
    ERROR_WEIGHT = 0.3
    SLOW_WEIGHT = 0.2
    MAX_RISK_SCORE = 1.0

    def analyze(self, logs: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze logs and return risk score + alerts."""
        errors = [
            log
            for log in logs
            if log.get("status_code", 200) >= self.ERROR_STATUS_THRESHOLD
        ]
        slow = [
            log
            for log in logs
            if log.get("duration_ms", 0) > self.SLOW_DURATION_THRESHOLD_MS
        ]

        total = max(len(logs), 1)
        risk_score = min(
            (len(errors) * self.ERROR_WEIGHT + len(slow) * self.SLOW_WEIGHT) / total,
            self.MAX_RISK_SCORE,
        )

        alerts: list[dict[str, str]] = []
        for e in errors:
            resource = e.get("resource", "unknown")
            alerts.append(
                {
                    "severity": "CRITICAL",
                    "message": f"Error on {resource}: status {e.get('status_code')}",
                    "log_id": e.get("log_id", ""),
                }
            )
        for s in slow:
            resource = s.get("resource", "unknown")
            alerts.append(
                {
                    "severity": "WARNING",
                    "message": f"Slow request on {resource}: {s.get('duration_ms')}ms",
                    "log_id": s.get("log_id", ""),
                }
            )

        return {
            "risk_score": round(risk_score, 4),
            "alerts": alerts,
            "errors_count": len(errors),
            "slow_count": len(slow),
        }
