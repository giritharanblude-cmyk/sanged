"""HTTP middleware: security headers, CSRF, Redis-backed rate limiting."""
import time

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config import settings
from app.core.security import CSRF_SAFE_METHODS, CsrfError, assert_csrf
from app.kernel.jobs import get_redis, redis_incr

PUBLIC_PATHS: tuple[str, ...] = (
    "/healthz",
    "/readyz",
)
# Paths where browser-side mutations happen without an authenticated user.
CSRF_EXEMPT_PATHS: frozenset[str] = frozenset(
    {"/api/v1/auth/login", "/api/v1/auth/verify-otp"}
)

# Handlers must never exceed their window counting cost; keys expire anyway.
RATE_KEY: str = "sangad:ratelimit:{bucket}:{window}"
SEGMENT_SECTION: int = 2


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Hardening headers on every response (V-SEC-01)."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # HSTS only has meaning over TLS;cookie_secure marks non-local envs.
        if settings.cookie_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=()"
        return response


class CsrfMiddleware(BaseHTTPMiddleware):
    """Enforce the double-submit token on unsafe methods to non-public paths."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if request.method in CSRF_SAFE_METHODS or path in CSRF_EXEMPT_PATHS:
            return await call_next(request)
        try:
            assert_csrf(request)
        except CsrfError as exc:
            return JSONResponse(
                status_code=403,
                content={"code": "csrf_failed", "detail": str(exc), "type": "about:blank"},
            )
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window counter per client IP, kept in Redis so it survives
    restarts and is shared across workers (T-701: the old version used a
    per-process dict that leaked memory and reset on every deploy)."""

    def __init__(
        self,
        app: FastAPI,
        max_requests: int = 600,
        window_seconds: int = 60,
        exempt: tuple[str, ...] = PUBLIC_PATHS,
    ) -> None:
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.exempt = exempt

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if path in self.exempt:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        bucket = self._bucket(client_ip, path)
        window = self._window()
        key = RATE_KEY.format(bucket=bucket, window=window)
        r = get_redis()

        count = redis_incr(key)
        if count == 1:
            r.expire(key, self.window_seconds)
        if count > self.max_requests:
            return JSONResponse(
                status_code=429,
                content={
                    "code": "rate_limited",
                    "detail": "Too many requests; slow down",
                    "type": "about:blank",
                },
            )
        return await call_next(request)

    @staticmethod
    def _bucket(client_ip: str, path: str) -> str:
        """One bucket per (ip, top-level API segment) so logs and dashboards
        can answer what is being throttled."""
        parts = [p for p in path.split("/") if p]
        # /api/v1/<section>/... -> the section name is the third part
        section = parts[2] if len(parts) > SEGMENT_SECTION else (parts[0] if parts else "root")
        return f"{client_ip}:{section}"

    def _window(self) -> str:
        """Bucket by fixed window start so counters line up with the TTL."""
        return str(int(time.time() // self.window_seconds))
