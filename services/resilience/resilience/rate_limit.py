"""Token-bucket rate limiting (deterministic, injectable clock/sleeper)."""

from __future__ import annotations

import time
from typing import Callable

_SLEEP_STEP = 0.01


class TokenBucket:
    """A token bucket with a steady refill rate and a hard capacity.

    ``acquire`` returns True when the requested tokens were taken (non-
    blocking by default). ``block=True`` waits until tokens are available
    (with an optional ``timeout``); ``False`` on timeout. Clock and sleeper
    are injectable for deterministic tests.
    """

    def __init__(
        self,
        rate: float,
        capacity: float,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if rate < 0:
            raise ValueError("rate must be >= 0")
        if capacity <= 0:
            raise ValueError("capacity must be > 0")
        self.rate = rate
        self.capacity = capacity
        self._tokens = capacity
        self._clock = clock
        self._sleeper = sleeper
        self._last = clock()

    def acquire(
        self,
        tokens: float = 1.0,
        *,
        block: bool = False,
        timeout: float | None = None,
    ) -> bool:
        """Take ``tokens`` from the bucket, refilling first. Returns False
        when unavailable (or on timeout in blocking mode)."""
        if tokens <= 0:
            raise ValueError("tokens must be > 0")
        if tokens > self.capacity:
            return False
        deadline: float | None = None
        if block and timeout is not None:
            if timeout < 0:
                raise ValueError("timeout must be >= 0")
            deadline = self._clock() + timeout
        while True:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            if not block:
                return False
            now = self._clock()
            if deadline is not None and now >= deadline:
                return False
            if deadline is None:
                self._sleeper(_SLEEP_STEP)
            else:
                self._sleeper(min(_SLEEP_STEP, deadline - now))

    def _refill(self) -> None:
        now = self._clock()
        elapsed = now - self._last
        if elapsed > 0:
            self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
            self._last = now
