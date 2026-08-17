from __future__ import annotations

import pytest
from resilience import RetryExhausted, is_retryable_error, retry
from tests.conftest import FakeSleeper, HttpLikeError, make_flaky


def test_success_first_attempt_returns_value_and_no_sleep(sleeper: FakeSleeper) -> None:
    def fn() -> str:
        return "ok"

    result = retry(fn, sleeper=sleeper)
    assert result == "ok"
    assert sleeper.calls == []


def test_success_after_transient_failures_backs_off_exponentially(
    sleeper: FakeSleeper,
) -> None:
    fn, stats = make_flaky(failures=2, error=HttpLikeError(503))
    result = retry(
        fn, retries=3, base_delay=1.0, max_delay=30.0, jitter=0.0, sleeper=sleeper
    )
    assert result == "ok"
    assert stats["calls"] == 3
    assert sleeper.calls == [1.0, 2.0]


def test_raises_retry_exhausted_after_all_attempts(sleeper: FakeSleeper) -> None:
    fn, stats = make_flaky(failures=99, error=HttpLikeError(500))
    with pytest.raises(RetryExhausted) as exc_info:
        retry(fn, retries=3, base_delay=1.0, jitter=0.0, sleeper=sleeper)
    assert stats["calls"] == 4
    assert isinstance(exc_info.value.__cause__, HttpLikeError)
    assert sleeper.calls == [1.0, 2.0, 4.0]


def test_non_retryable_error_raises_immediately_without_sleep(
    sleeper: FakeSleeper,
) -> None:
    fn, stats = make_flaky(failures=99, error=HttpLikeError(400))
    with pytest.raises(HttpLikeError):
        retry(fn, retries=3, base_delay=1.0, sleeper=sleeper)
    assert stats["calls"] == 1
    assert sleeper.calls == []


def test_custom_retryable_callable_is_used(sleeper: FakeSleeper) -> None:
    fn, stats = make_flaky(failures=2, error=ValueError("boom"))
    retry(
        fn,
        retries=3,
        sleeper=sleeper,
        retryable=lambda exc: isinstance(exc, ValueError),
    )
    assert stats["calls"] == 3


def test_retries_zero_single_attempt(sleeper: FakeSleeper) -> None:
    fn, stats = make_flaky(failures=1, error=HttpLikeError(500))
    with pytest.raises(RetryExhausted):
        retry(fn, retries=0, sleeper=sleeper)
    assert stats["calls"] == 1
    assert sleeper.calls == []


def test_jitter_bounds_delay(sleeper: FakeSleeper) -> None:
    fn, _ = make_flaky(failures=1, error=HttpLikeError(500))
    retry(fn, retries=1, base_delay=10.0, jitter=0.5, sleeper=sleeper)
    assert sleeper.calls[0] >= 10.0
    assert sleeper.calls[0] <= 15.0


def test_max_delay_caps_backoff(sleeper: FakeSleeper) -> None:
    fn, _ = make_flaky(failures=99, error=HttpLikeError(500))
    with pytest.raises(RetryExhausted):
        retry(fn, retries=5, base_delay=1.0, max_delay=3.0, jitter=0.0, sleeper=sleeper)
    assert sleeper.calls == [1.0, 2.0, 3.0, 3.0, 3.0]


def test_validation_rejects_bad_arguments(sleeper: FakeSleeper) -> None:
    fn, _ = make_flaky(failures=1)
    with pytest.raises(ValueError, match="retries"):
        retry(fn, retries=-1, sleeper=sleeper)
    with pytest.raises(ValueError, match="base_delay"):
        retry(fn, base_delay=-1.0, sleeper=sleeper)
    with pytest.raises(ValueError, match="max_delay"):
        retry(fn, base_delay=5.0, max_delay=2.0, sleeper=sleeper)


def test_is_retryable_error_classifies_codes_and_types() -> None:
    assert is_retryable_error(HttpLikeError(429))
    assert is_retryable_error(HttpLikeError(500))
    assert is_retryable_error(HttpLikeError(503))
    assert not is_retryable_error(HttpLikeError(400))
    assert not is_retryable_error(HttpLikeError(401))
    assert is_retryable_error(TimeoutError("slow"))
    assert is_retryable_error(ConnectionError("reset"))
    assert is_retryable_error(ConnectionResetError("reset"))
    assert is_retryable_error(OSError("connection refused")) is False
    assert is_retryable_error(ValueError("boom")) is False


def test_is_retryable_error_urllib_shapes() -> None:
    class URLError(RuntimeError):
        pass

    class RemoteDisconnected(ConnectionResetError):
        pass

    assert is_retryable_error(URLError("no route"))
    assert is_retryable_error(RemoteDisconnected("closed"))
