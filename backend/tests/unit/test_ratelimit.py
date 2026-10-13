from app.core.ratelimit import RateLimiter


def test_allows_up_to_the_limit_then_blocks() -> None:
    limiter = RateLimiter()
    assert [limiter.check("a", 3, 60, now=float(i)) for i in range(3)] == [None, None, None]
    retry_after = limiter.check("a", 3, 60, now=3.0)
    assert retry_after == 57


def test_allows_again_after_the_window() -> None:
    limiter = RateLimiter()
    for i in range(3):
        limiter.check("a", 3, 60, now=float(i))
    assert limiter.check("a", 3, 60, now=3.0) is not None
    assert limiter.check("a", 3, 60, now=61.0) is None


def test_keys_are_independent() -> None:
    limiter = RateLimiter()
    limiter.check("a", 1, 60, now=0.0)
    assert limiter.check("a", 1, 60, now=1.0) is not None
    assert limiter.check("b", 1, 60, now=1.0) is None
