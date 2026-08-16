from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ValidationError


class SalesforceLog(BaseModel):
    log_id: str
    timestamp: str
    org_id: str
    status_code: int
    duration_ms: int
    resource: str
    severity: str = "INFO"
    message: str = ""
    retried: bool = False
    object_name: str = ""
    object_id: str = ""


class LogCollector:
    """Collects and validates Salesforce logs from mock data."""

    def load(self, raw_logs: list[dict[str, Any]]) -> list[SalesforceLog]:
        """Load raw log dicts into validated SalesforceLog models."""
        return [SalesforceLog(**log) for log in raw_logs]

    def validate(self, raw_logs: list[dict[str, Any]]) -> dict[str, Any]:
        """Validate all logs against schema. Returns valid flag + errors."""
        errors: list[str] = []
        for i, log in enumerate(raw_logs):
            try:
                SalesforceLog(**log)
            except ValidationError as e:
                errors.append(f"Log {i}: {str(e)}")
        return {"valid": len(errors) == 0, "errors": errors}
