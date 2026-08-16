from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Alert(BaseModel):
    severity: str
    message: str
    log_id: str = ""
    timestamp: str = ""


class HeuristicEngine:
    """Applies rule-based heuristics to analyze Salesforce logs."""

    def analyze(self, logs: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze logs and return risk score + alerts."""
        errors = [l for l in logs if l.get("status_code", 200) >= 500]
        slow = [l for l in logs if l.get("duration_ms", 0) > 1000]

        total = max(len(logs), 1)
        risk_score = min((len(errors) * 0.3 + len(slow) * 0.2) / total, 1.0)

        alerts: list[dict[str, str]] = []
        for e in errors:
            alerts.append({
                "severity": "CRITICAL",
                "message": f"Error on {e.get('resource', 'unknown')}: status {e.get('status_code')}",
                "log_id": e.get("log_id", ""),
            })
        for s in slow:
            alerts.append({
                "severity": "WARNING",
                "message": f"Slow request on {s.get('resource', 'unknown')}: {s.get('duration_ms')}ms",
                "log_id": s.get("log_id", ""),
            })

        return {
            "risk_score": round(risk_score, 4),
            "alerts": alerts,
            "errors_count": len(errors),
            "slow_count": len(slow),
        }
