"""Retry with exponential backoff + jitter for transient transport errors."""

from __future__ import annotations

import random
import time
from typing import Callable, TypeVar

T = TypeVar("T")

# urllib/httplib error class names that mean "the transport glitched, retry".
_RETRYABLE_TYPE_NAMES = frozenset({"URLError", "RemoteDisconnected", "IncompleteRead"})


class RetryExhausted(RuntimeError):
    """Raised when all retry attempts fail (last error is the cause)."""


def is_retryable_error(exc: BaseException) -> bool:
    """True for transient transport errors: HTTP 429/5xx, timeouts, resets.

    Non-transient errors (4xx other than 429, auth, protocol/validation
    failures) return False so callers fail fast instead of retrying.
    """
    code = getattr(exc, "code", None)
    if isinstance(code, int) and (code == 429 or 500 <= code <= 599):
        return True
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    return type(exc).__name__ in _RETRYABLE_TYPE_NAMES


def retry(
    fn: Callable[[], T],
    *,
    retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: float = 0.1,
    retryable: Callable[[BaseException], bool] = is_retryable_error,
    sleeper: Callable[[float], None] = time.sleep,
) -> T:
    """Call ``fn`` retrying retryable failures with exponential backoff.

    Delays follow ``base_delay * 2**attempt`` capped at ``max_delay``, with
    optional multiplicative jitter (``delay * (1 + uniform(0, jitter))``).
    Non-retryable errors re-raise immediately; exhausting all attempts
    raises :class:`RetryExhausted` with the last error as cause.
    ``sleeper`` is injectable for deterministic tests.
    """
    if retries < 0:
        raise ValueError("retries must be >= 0")
    if base_delay < 0:
        raise ValueError("base_delay must be >= 0")
    if max_delay < base_delay:
        raise ValueError("max_delay must be >= base_delay")

    attempt = 0
    while True:
        try:
            return fn()
        except Exception as exc:
            if not retryable(exc):
                raise
            if attempt >= retries:
                raise RetryExhausted(f"exhausted {retries} retries") from exc
            delay = min(max_delay, base_delay * (2**attempt))
            if jitter > 0:
                delay *= 1 + random.uniform(0, jitter)
            sleeper(delay)
            attempt += 1
