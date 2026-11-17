"""Limits on how often sensitive actions can be repeated.

Without a limit, someone could try thousands of passwords, flood a person
with reset emails, or fill the disk with uploads.

This limiter keeps its counts in the memory of the running process. That
is simple and needs no extra service, and it is correct while the API runs
as a single process. If the API is later run as several processes, each
would count separately; that is the moment to move the counts into a
shared store such as Redis (see the roadmap's note on Redis).
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import Request

from app.core.config import get_settings
from app.core.errors import RateLimitError


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, *, limit: int, window_seconds: int) -> None:
        """Record one attempt for `key`; raise if it is over the limit."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            # Forget attempts older than the window.
            while hits and hits[0] <= now - window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                raise RateLimitError("Too many attempts. Please wait a little and try again.")
            hits.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()


def client_address(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def rate_limit(name: str, *, limit: int, window_seconds: int) -> Callable[[Request], None]:
    """Build a FastAPI dependency that limits one endpoint per client address.

    @router.post("/login", dependencies=[Depends(rate_limit("login", ...))])
    """

    def dependency(request: Request) -> None:
        if not get_settings().rate_limits_enabled:
            return
        limiter.check(
            f"{name}:{client_address(request)}", limit=limit, window_seconds=window_seconds
        )

    return dependency
