"""Feedback loop engines (Phase 4).

Accuracy tracking, user feedback ingestion and threshold calibration —
all observational, none of them decide anything (see
docs/FEEDBACK_LOOP_SPEC.md).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from pydantic import BaseModel


class AccuracyResult(BaseModel):
    status: str = "no_data"  # "evaluated" | "no_data"
    direction_expected: str | None = None  # "up" | "down" | "flat"
    direction_actual: str | None = None  # "up" | "down" | "flat"
    forecast_hit: bool | None = None  # direction confirmed; None = indeterminate
    anomaly_flagged: bool = False
    anomaly_hit: bool | None = None
    false_positive: bool = False
    series_actual: list[float] = []


class FeedbackRecord(BaseModel):
    id: str
    target: str  # "anomaly" | "alert"
    action: str  # "true_positive" | "false_positive"
    timestamp: str | None = None
    note: str | None = None


class FeedbackFile(BaseModel):
    loaded: int
    valid: int
    invalid: int
    by_action: dict[str, int]
    by_target: dict[str, int]
    records: list[FeedbackRecord] = []


class Calibration(BaseModel):
    status: str  # "insufficient" | "recommended"
    samples: int
    avg_fp_rate: float | None = None
    current_threshold: float | None = None
    recommended_threshold: float | None = None


_DIRECTION_EPS = 1e-9


def accuracy_direction(delta: float) -> str:
    """Map a signed delta to a direction label ("up" | "down" | "flat")."""
    if delta > _DIRECTION_EPS:
        return "up"
    if delta < -_DIRECTION_EPS:
        return "down"
    return "flat"


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


class AccuracyTracker:
    """Evaluate the previous snapshot's shadow_mode against reality.

    Compares the forecast direction (slope) with the direction observed in
    the current series, and whether a flagged anomaly was followed by a real
    peak (sustained above the previous baseline). Flat forecasts are
    indeterminate — they score neither hit nor miss.
    """

    def evaluate(self, prev: dict, current: dict) -> AccuracyResult:
        prev_shadow = prev.get("shadow_mode") or {}
        if not prev_shadow.get("enabled"):
            return AccuracyResult()

        forecast = prev_shadow.get("forecast") or {}
        anomalies = prev_shadow.get("anomalies") or {}
        prev_series = [float(v) for v in (prev_shadow.get("series") or [])]
        if not forecast or not anomalies:
            return AccuracyResult()
        if not all(math.isfinite(v) for v in prev_series):
            raise ValueError("series must contain only finite values")

        current_shadow = current.get("shadow_mode") or {}
        actual = [float(v) for v in (current_shadow.get("series") or [])]
        if not actual:
            return AccuracyResult()
        if not all(math.isfinite(v) for v in actual):
            raise ValueError("series must contain only finite values")
        if len(actual) < 2:
            return AccuracyResult()

        slope = float(forecast.get("slope", 0.0))
        expected = accuracy_direction(slope)
        observed = accuracy_direction(actual[-1] - actual[0])
        forecast_hit = None if expected == "flat" else expected == observed

        flagged = int(anomalies.get("count", 0)) > 0
        anomaly_hit: bool | None = None
        false_positive = False
        if flagged:
            baseline = _median(prev_series) if prev_series else 0.0
            peak_real = max(actual) > (baseline * 1.5 if baseline > 0 else baseline)
            anomaly_hit = peak_real
            false_positive = not peak_real

        return AccuracyResult(
            status="evaluated",
            direction_expected=expected,
            direction_actual=observed,
            forecast_hit=forecast_hit,
            anomaly_flagged=flagged,
            anomaly_hit=anomaly_hit,
            false_positive=false_positive,
            series_actual=actual,
        )


class FeedbackStore:
    """Load and validate a user-supplied feedback.json file.

    The file is a JSON list of records ``{"id", "target", "action"}`` where
    ``target`` is ``anomaly`` or ``alert`` and ``action`` is
    ``true_positive`` or ``false_positive``. Invalid rows are skipped and
    counted — one bad row never breaks the pipeline.
    """

    def __init__(
        self,
        allowed_targets: tuple[str, ...] = ("anomaly", "alert"),
        allowed_actions: tuple[str, ...] = ("true_positive", "false_positive"),
    ) -> None:
        self.allowed_targets = allowed_targets
        self.allowed_actions = allowed_actions

    def load(self, path: str | Path) -> FeedbackFile:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"feedback file not found: {path}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON in feedback file {path}: {exc}") from exc
        if not isinstance(data, list):
            raise ValueError(f"feedback file {path} must contain a JSON list")

        records: list[FeedbackRecord] = []
        invalid = 0
        for row in data:
            record = self._parse_row(row)
            if record is None:
                invalid += 1
                continue
            records.append(record)

        by_action: dict[str, int] = {}
        by_target: dict[str, int] = {}
        for record in records:
            by_action[record.action] = by_action.get(record.action, 0) + 1
            by_target[record.target] = by_target.get(record.target, 0) + 1

        return FeedbackFile(
            loaded=len(data),
            valid=len(records),
            invalid=invalid,
            by_action=by_action,
            by_target=by_target,
            records=records,
        )

    def _parse_row(self, row: object) -> FeedbackRecord | None:
        if not isinstance(row, dict):
            return None
        record_id = row.get("id")
        target = row.get("target")
        action = row.get("action")
        if not isinstance(record_id, str) or not record_id:
            return None
        if target not in self.allowed_targets or action not in self.allowed_actions:
            return None
        return FeedbackRecord(
            id=record_id,
            target=target,
            action=action,
            timestamp=(
                row.get("timestamp") if isinstance(row.get("timestamp"), str) else None
            ),
            note=row.get("note") if isinstance(row.get("note"), str) else None,
        )


class SampleStore:
    """Accumulate calibration observations ``{threshold, fp_rate}``.

    One observation per cycle that flagged an anomaly (a correct rejection
    carries no FP information). The window is rolling — only the last
    ``max_samples`` observations count, so the calibration tracks the current
    reality. Missing file means an empty window (first run); invalid JSON is
    a loud ``ValueError`` so the pipeline records it as a step error instead
    of silently resetting the history.
    """

    def __init__(self, max_samples: int = 50) -> None:
        self.max_samples = max_samples

    def load(self, path: str | Path) -> list[dict]:
        path = Path(path)
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON in samples file {path}: {exc}") from exc
        if not isinstance(data, list):
            raise ValueError(f"samples file {path} must contain a JSON list")
        return [row for row in data if isinstance(row, dict)]

    def add(self, samples: list[dict], threshold: float, fp_rate: float) -> list[dict]:
        return (samples + [{"threshold": threshold, "fp_rate": fp_rate}])[
            -self.max_samples :
        ]

    def save(self, path: str | Path, samples: list[dict]) -> None:
        Path(path).write_text(json.dumps(samples, indent=2) + "\n", encoding="utf-8")


class Calibrator:
    """Recommend an AnomalyEngine threshold from observed false-positive rates.

    The engines are deterministic (no trainable weights), so "retraining" is
    threshold calibration: when the average FP rate exceeds the target the
    threshold goes up; when it is below half the target it goes down; in
    between it stays. The recommendation is never applied automatically.
    """

    def __init__(
        self,
        target_fp_rate: float = 0.2,
        min_samples: int = 3,
        min_threshold: float = 2.0,
        max_threshold: float = 6.0,
        step: float = 0.5,
    ) -> None:
        self.target_fp_rate = target_fp_rate
        self.min_samples = min_samples
        self.min_threshold = min_threshold
        self.max_threshold = max_threshold
        self.step = step

    def recommend(self, samples: list[dict]) -> Calibration:
        if len(samples) < self.min_samples:
            return Calibration(status="insufficient", samples=len(samples))

        thresholds: list[float] = []
        fp_rates: list[float] = []
        for sample in samples:
            threshold = float(sample["threshold"])
            fp_rate = float(sample["fp_rate"])
            if not math.isfinite(threshold) or not math.isfinite(fp_rate):
                raise ValueError("samples must contain only finite values")
            if not 0.0 <= fp_rate <= 1.0:
                raise ValueError("fp_rate must be between 0 and 1")
            thresholds.append(threshold)
            fp_rates.append(fp_rate)

        avg_fp = sum(fp_rates) / len(fp_rates)
        current = sum(thresholds) / len(thresholds)

        if avg_fp > self.target_fp_rate:
            recommended = current + self.step
        elif avg_fp < self.target_fp_rate / 2:
            recommended = current - self.step / 2
        else:
            recommended = current

        recommended = min(max(recommended, self.min_threshold), self.max_threshold)
        return Calibration(
            status="recommended",
            samples=len(samples),
            avg_fp_rate=avg_fp,
            current_threshold=current,
            recommended_threshold=recommended,
        )
