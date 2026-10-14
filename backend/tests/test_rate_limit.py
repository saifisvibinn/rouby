import pytest
from app.core.rate_limit import RateLimitExceeded, SlidingWindowRateLimiter


def test_login_rate_limiter_trips_after_max_calls() -> None:
    limiter = SlidingWindowRateLimiter(max_calls=3, window_seconds=60.0)
    limiter.check("a")
    limiter.check("a")
    limiter.check("a")
    with pytest.raises(RateLimitExceeded):
        limiter.check("a")
