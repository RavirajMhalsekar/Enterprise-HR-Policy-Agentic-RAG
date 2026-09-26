import time
from collections import defaultdict, deque
from threading import Lock
from fastapi import HTTPException, status

_locks = Lock()
_request_history: dict[str, deque[float]] = defaultdict(deque)


def check_rate_limit(key: str, max_requests: int, window_seconds: int) -> None:
    """
    In-memory sliding-window rate limiter.
    Records epoch timestamps and evicts timestamps older than window_seconds.
    Raises HTTP 429 when max_requests within window is exceeded.
    """
    now = time.time()
    cutoff = now - window_seconds

    with _locks:
        history = _request_history[key]

        # Evict timestamps outside the sliding window
        while history and history[0] < cutoff:
            history.popleft()

        if len(history) >= max_requests:
            oldest_ts = history[0]
            retry_after = max(1, int(window_seconds - (now - oldest_ts)))
            time_unit = f"{window_seconds // 60} minutes" if window_seconds >= 60 else f"{window_seconds} seconds"
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: maximum {max_requests} requests per {time_unit}. Please retry in {retry_after}s.",
                headers={"Retry-After": str(retry_after)},
            )

        history.append(now)


def reset_rate_limits() -> None:
    """Helper to clear rate limiter history (useful for automated testing)."""
    with _locks:
        _request_history.clear()
