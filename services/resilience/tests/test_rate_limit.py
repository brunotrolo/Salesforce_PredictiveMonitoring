from __future__ import annotations

import pytest
from resilience import TokenBucket
from tests.conftest import FakeClock, FakeSleeper


def test_starts_full(clock: FakeClock) -> None:
    bucket = TokenBucket(rate=1.0, capacity=3.0, clock=clock)
    assert bucket.acquire()
    assert bucket.acquire()
    assert bucket.acquire()
    assert not bucket.acquire()


def test_refills_over_time(clock: FakeClock) -> None:
    bucket = TokenBucket(rate=1.0, capacity=1.0, clock=clock)
    assert bucket.acquire()
    assert not bucket.acquire()
    clock.advance(1.0)
    assert bucket.acquire()
    clock.advance(0.5)
    assert not bucket.acquire()
    clock.advance(0.5)
    assert bucket.acquire()


def test_capacity_is_hard_limit(clock: FakeClock) -> None:
    bucket = TokenBucket(rate=10.0, capacity=2.0, clock=clock)
    assert bucket.acquire(2)
    assert not bucket.acquire(2)
    clock.advance(10.0)
    assert bucket.acquire(2)


def test_acquire_more_than_capacity_returns_false(clock: FakeClock) -> None:
    bucket = TokenBucket(rate=1.0, capacity=1.0, clock=clock)
    assert not bucket.acquire(2.0)


def test_validation(clock: FakeClock) -> None:
    with pytest.raises(ValueError, match="rate"):
        TokenBucket(rate=-1.0, capacity=1.0, clock=clock)
    with pytest.raises(ValueError, match="capacity"):
        TokenBucket(rate=1.0, capacity=-1.0, clock=clock)
    bucket = TokenBucket(rate=1.0, capacity=1.0, clock=clock)
    with pytest.raises(ValueError, match="tokens"):
        bucket.acquire(0.0)
    with pytest.raises(ValueError, match="timeout"):
        bucket.acquire(block=True, timeout=-0.1)


def test_zero_rate_never_refills(clock: FakeClock) -> None:
    bucket = TokenBucket(rate=0.0, capacity=1.0, clock=clock)
    assert bucket.acquire()
    clock.advance(60.0)
    assert not bucket.acquire()


def test_block_acquire_succeeds_after_refill(
    clock: FakeClock, sleeper: FakeSleeper
) -> None:
    bucket = TokenBucket(rate=2.0, capacity=1.0, clock=clock, sleeper=sleeper)
    assert bucket.acquire()
    assert bucket.acquire(block=True)
    assert clock.now == pytest.approx(1000.5, abs=0.02)


def test_block_acquire_timeout_returns_false(
    clock: FakeClock, sleeper: FakeSleeper
) -> None:
    bucket = TokenBucket(rate=0.0, capacity=1.0, clock=clock, sleeper=sleeper)
    assert bucket.acquire()
    assert not bucket.acquire(block=True, timeout=0.1)
    assert clock.now == pytest.approx(1000.1, abs=0.02)


def test_block_without_timeout_keeps_trying(
    clock: FakeClock, sleeper: FakeSleeper
) -> None:
    bucket = TokenBucket(rate=1.0, capacity=1.0, clock=clock, sleeper=sleeper)
    assert bucket.acquire()
    assert bucket.acquire(block=True)
    assert clock.now == pytest.approx(1001.0, abs=0.02)


def test_acquire_partial_tokens(clock: FakeClock) -> None:
    bucket = TokenBucket(rate=1.0, capacity=2.0, clock=clock)
    for _ in range(4):
        assert bucket.acquire(0.5)
    assert not bucket.acquire(0.5)
    clock.advance(0.5)
    assert bucket.acquire(0.5)


def test_exposes_rate_and_capacity(clock: FakeClock) -> None:
    bucket = TokenBucket(rate=2.0, capacity=5.0, clock=clock)
    assert bucket.rate == 2.0
    assert bucket.capacity == 5.0
