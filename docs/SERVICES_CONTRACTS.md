# Service Input/Output Contracts (JSON Schema)

Phase 0 uses Python dicts; Phase 1 will formalize these as Pydantic models.

---

## Collector Service

**Input:** `List[dict]` (raw Salesforce log entries)
```json
[
  {
    "log_id": "string",
    "timestamp": "ISO-8601",
    "org_id": "string",
    "status_code": 200,
    "duration_ms": 150,
    "resource": "/api/..."
  }
]
```

**Output:** `dict`
```json
{
  "valid": true,
  "errors": []
}
```

---

## Heuristic Service

**Input:** `List[dict]` (validated log entries from Collector)
```json
[
  {
    "log_id": "string",
    "status_code": 200,
    "duration_ms": 150,
    "resource": "/api/..."
  }
]
```

**Output:** `dict`
```json
{
  "risk_score": 0.42,
  "alerts": [
    {
      "severity": "CRITICAL|WARNING",
      "message": "string",
      "log_id": "string"
    }
  ],
  "errors_count": 1,
  "slow_count": 1
}
```

---

## Comparison Service

**Input:**
- `current: dict` (from Heuristic)
- `historical: dict | None` (baseline; defaults to zero if absent)

**Output:** `ComparisonResult`
```json
{
  "prediction": "STABLE|MODERATE_INCREASE|CRITICAL_INCREASE|IMPROVEMENT",
  "confidence": 0.95,
  "risk_delta": 0.30,
  "summary": "Risk changed by +0.3000 (CRITICAL_INCREASE)"
}
```

---

## Full Pipeline Output

**File:** `monitoring_output.json`
```json
{
  "timestamp": "ISO-8601",
  "risk_score": 0.42,
  "errors_count": 1,
  "slow_requests_count": 1,
  "alerts": [],
  "comparison": {
    "prediction": "CRITICAL_INCREASE",
    "confidence": 0.9,
    "risk_delta": 0.42,
    "summary": "..."
  },
  "health_check": {
    "status": "HEALTHY|WARNING",
    "last_updated": "ISO-8601"
  },
  "validation": {
    "valid": true,
    "errors": []
  },
  "logs_processed": 3
}
```
