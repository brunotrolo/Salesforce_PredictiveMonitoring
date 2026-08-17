from __future__ import annotations

import pytest


class FakeClock:
    """Incrementable monotonic clock for deterministic timing tests."""

    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeSleeper:
    """Records sleep calls; optionally advances a FakeClock when it sleeps."""

    def __init__(self, clock: FakeClock | None = None) -> None:
        self.calls: list[float] = []
        self._clock = clock

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)
        if self._clock is not None:
            self._clock.advance(seconds)


class HttpLikeError(RuntimeError):
    """Error with an HTTP-ish status code (urllib HTTPError shape)."""

    def __init__(self, code: int, message: str | None = None) -> None:
        super().__init__(message or f"HTTP {code}")
        self.code = code


def make_flaky(failures: int, error: BaseException | None = None) -> tuple:
    """Return (fn, stats) where fn raises ``error`` the first ``failures`` times.

    ``stats`` is a dict with ``{"calls": int}`` to assert call counts.
    """
    stats = {"calls": 0}
    failure = error if error is not None else HttpLikeError(500)

    def fn() -> str:
        stats["calls"] += 1
        if stats["calls"] <= failures:
            raise failure
        return "ok"

    return fn, stats


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def sleeper(clock: FakeClock) -> FakeSleeper:
    return FakeSleeper(clock)
