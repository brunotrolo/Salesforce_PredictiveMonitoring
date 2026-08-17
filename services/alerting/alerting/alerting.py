from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class AggregatedAlert(BaseModel):
    """An alert grouped by key (severity + resource + kind).

    ``count`` is the number of raw alerts merged into this group within the
    current snapshot; ``recurring``/``repeat_count`` track how many previous
    snapshots contained the same key (alert fatigue prevention).
    """

    key: str
    severity: str
    resource: str
    kind: str
    message: str
    count: int = 1
    log_ids: list[str] = []
    first_seen: str = ""
    last_seen: str = ""
    recurring: bool = False
    repeat_count: int = 0


SEVERITY_RANK = {"INFO": 0, "WARNING": 1, "CRITICAL": 2}


class AlertAggregator:
    """Aggregates and deduplicates raw alerts into grouped summaries.

    Raw alerts from the heuristic engine are merged by a canonical key
    (severity + kind + resource), so N identical errors on the same endpoint
    become one alert with ``count=N``.  A ``history`` mapping (key -> number
    of previous snapshots where the key appeared) marks recurring alerts,
    enabling severity escalation downstream without alert fatigue.
    """

    def key_for(self, alert: dict[str, Any]) -> str:
        severity = str(alert.get("severity", "INFO")).upper()
        kind = str(alert.get("kind", alert.get("resource", "unknown"))).upper()
        resource = str(alert.get("resource", "unknown")).upper()
        return f"{severity}|{kind}|{resource}"

    def severity_counts(self, alerts: list[AggregatedAlert]) -> dict[str, int]:
        counts = {"INFO": 0, "WARNING": 0, "CRITICAL": 0}
        for a in alerts:
            rank = a.severity.upper()
            if rank in counts:
                counts[rank] += 1
        return counts

    def aggregate(
        self,
        alerts: list[dict[str, Any]],
        history: dict[str, int] | None = None,
    ) -> list[AggregatedAlert]:
        """Merge raw alerts by key and annotate recurrence from ``history``."""
        history = history or {}
        groups: dict[str, AggregatedAlert] = {}

        for alert in alerts:
            severity = str(alert.get("severity", "INFO")).upper()
            key = self.key_for(alert)
            group = groups.get(key)
            if group is None:
                group = AggregatedAlert(
                    key=key,
                    severity=severity,
                    resource=str(alert.get("resource", "unknown")),
                    kind=str(alert.get("kind", "unknown")),
                    message=str(alert.get("message", "")),
                    log_ids=[],
                    count=0,
                )
                groups[key] = group

            group.count += 1
            log_id = str(alert.get("log_id", ""))
            if log_id and len(group.log_ids) < 20:
                group.log_ids.append(log_id)
            ts = str(alert.get("timestamp", ""))
            if ts:
                if not group.first_seen or ts < group.first_seen:
                    group.first_seen = ts
                if ts > group.last_seen:
                    group.last_seen = ts

        result = list(groups.values())
        for group in result:
            repeat = history.get(group.key, 0)
            group.recurring = repeat > 0
            group.repeat_count = repeat

        result.sort(
            key=lambda a: (
                -SEVERITY_RANK.get(a.severity.upper(), 0),
                -a.count,
                a.message,
            )
        )
        return result

    @classmethod
    def history_from_snapshot(cls, snapshot: dict[str, Any]) -> dict[str, int]:
        """Extract a recurrence history mapping from a previous snapshot.

        Works with snapshots that already carry ``alerts_aggregated`` (new
        pipeline) or raw ``alerts`` (legacy snapshots).
        """
        history: dict[str, int] = {}
        aggregated = snapshot.get("alerts_aggregated")
        if isinstance(aggregated, list):
            for a in aggregated:
                key = a.get("key", "")
                if not key:
                    continue
                previous = int(a.get("repeat_count", 0))
                history[key] = previous + 1 if a.get("recurring") else 1
            return history

        raw = snapshot.get("alerts", [])
        if isinstance(raw, list):
            for alert in raw:
                severity = str(alert.get("severity", "INFO")).upper()
                kind = str(alert.get("kind", alert.get("resource", "unknown"))).upper()
                resource = str(alert.get("resource", "unknown")).upper()
                key = f"{severity}|{kind}|{resource}"
                history[key] = history.get(key, 0) + 1
        return history
