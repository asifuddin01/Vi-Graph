"""Request limits (spec §29): upload size and a rate limit for expensive inference."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class BodySizeLimitMiddleware:
    """Rejects request bodies over ``max_bytes`` with 413.

    Checks Content-Length up front, and also counts bytes as they stream in, so chunked
    uploads without a Content-Length are cut off too, before being fully received.
    """

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = dict(scope["headers"]).get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > self.max_bytes:
            await self._reject()(scope, receive, send)
            return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    # FastAPI re-raises HTTPExceptions from body parsing unchanged.
                    raise HTTPException(status_code=413, detail=self._detail())
            return message

        await self.app(scope, limited_receive, send)

    def _detail(self) -> str:
        return f"request body is larger than {self.max_bytes // (1024 * 1024)} MB"

    def _reject(self) -> JSONResponse:
        return JSONResponse({"detail": self._detail()}, status_code=413)


class SlidingWindowLimiter:
    """At most ``limit`` requests per client per ``window_seconds``; limit 0 disables."""

    def __init__(
        self,
        limit: int,
        window_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def retry_after(self, client: str) -> float | None:
        """Record a request; None if allowed, else seconds until the next one would be."""
        if self.limit <= 0:
            return None
        now = self._clock()
        with self._lock:
            hits = self._hits[client]
            while hits and now - hits[0] >= self.window_seconds:
                hits.popleft()
            if len(hits) >= self.limit:
                return self.window_seconds - (now - hits[0])
            hits.append(now)
            return None
