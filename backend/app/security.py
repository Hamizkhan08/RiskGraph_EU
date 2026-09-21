from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Cross-Origin-Resource-Policy": "same-site",
}


class SecurityHeaders(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        resp = await call_next(request)
        for k, v in SECURITY_HEADERS.items():
            resp.headers.setdefault(k, v)
        if request.method != "GET":
            resp.headers["Cache-Control"] = "no-store"
        return resp


class RateLimiter(BaseHTTPMiddleware):
    """Sliding-window limiter per client address (in-memory; adequate for a single-instance demo).

    Behind a proxy every request may share one address; a shared store (e.g. Redis) or the platform's
    edge limiter is required for multi-instance production use. See docs/SECURITY_REVIEW.md."""

    def __init__(self, app, per_minute: int):
        super().__init__(app)
        self.per_minute = per_minute
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/health" or self.per_minute <= 0:
            return await call_next(request)
        ip = request.client.host if request.client else "unknown"
        now, q = time.monotonic(), self.hits[ip]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= self.per_minute:
            return JSONResponse({"detail": "rate limit exceeded"}, status_code=429, headers={"Retry-After": "30"})
        q.append(now)
        if len(self.hits) > 10_000:  # bound memory
            self.hits.clear()
        return await call_next(request)
