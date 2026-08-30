"""Per-IP rate limiting for the expensive endpoints.

Deliberately in-process and in-memory: this exists to keep a public demo from burning a
day's Gemini quota in one visit, not to be a real API gateway. That means limits reset on
restart and aren't shared across replicas — fine for a single-instance demo, and the point
where you'd outgrow it is the point where you'd want a real limiter (Redis) anyway.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.core.config import get_settings

settings = get_settings()

_WINDOW_SECONDS = 3600

_hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def _client_ip(request: Request) -> str:
    # Behind nginx/a platform proxy the socket peer is the proxy, so prefer the
    # forwarded header when present. Spoofable, but a determined abuser isn't the
    # threat model here — accidental quota exhaustion is.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce(request: Request, bucket: str, limit: int) -> None:
    """Raises 429 if this IP has exceeded `limit` requests for `bucket` in the last hour."""
    if not settings.rate_limit_enabled or limit <= 0:
        return

    key = (_client_ip(request), bucket)
    now = time.monotonic()
    cutoff = now - _WINDOW_SECONDS

    with _lock:
        timestamps = _hits[key]
        while timestamps and timestamps[0] < cutoff:
            timestamps.popleft()

        if len(timestamps) >= limit:
            retry_after = int(timestamps[0] + _WINDOW_SECONDS - now) + 1
            raise HTTPException(
                429,
                f"Rate limit reached for this action ({limit}/hour). Try again in "
                f"{retry_after // 60 or 1} minute(s).",
                headers={"Retry-After": str(retry_after)},
            )

        timestamps.append(now)
