from app.api.limits import SlidingWindowLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_requests_within_the_limit_are_allowed() -> None:
    limiter = SlidingWindowLimiter(3, window_seconds=60, clock=FakeClock())

    assert [limiter.retry_after("a") for _ in range(3)] == [None, None, None]


def test_request_over_the_limit_reports_when_to_retry() -> None:
    clock = FakeClock()
    limiter = SlidingWindowLimiter(2, window_seconds=60, clock=clock)
    limiter.retry_after("a")
    clock.now += 10
    limiter.retry_after("a")
    clock.now += 5

    assert limiter.retry_after("a") == 45  # the first hit leaves the window in 45s


def test_window_slides() -> None:
    clock = FakeClock()
    limiter = SlidingWindowLimiter(1, window_seconds=60, clock=clock)
    limiter.retry_after("a")
    clock.now += 60

    assert limiter.retry_after("a") is None


def test_rejected_requests_do_not_count() -> None:
    clock = FakeClock()
    limiter = SlidingWindowLimiter(1, window_seconds=60, clock=clock)
    limiter.retry_after("a")
    for _ in range(5):
        limiter.retry_after("a")
    clock.now += 60

    assert limiter.retry_after("a") is None


def test_clients_are_limited_independently() -> None:
    limiter = SlidingWindowLimiter(1, clock=FakeClock())
    limiter.retry_after("a")

    assert limiter.retry_after("b") is None
    assert limiter.retry_after("a") is not None


def test_zero_disables_the_limit() -> None:
    limiter = SlidingWindowLimiter(0, clock=FakeClock())

    assert all(limiter.retry_after("a") is None for _ in range(100))
