"""FastAPI entry point: middleware, routers, health/readiness, SPA serving."""
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any, cast

from fastapi import Depends, FastAPI, Request, Response
from fastapi import status as fastapi_status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.config import settings
from app.core.db import SessionLocal, engine
from app.core.errors import AppError, app_error_handler
from app.core.logging import setup_logging
from app.core.middleware import (
    CsrfMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.security import CsrfError, require_user
from app.kernel.files import probe_storage
from app.kernel.jobs import get_redis
from app.kernel.models import User
from app.modules.bills.router import router as bills_router
from app.modules.company.router import router as company_router
from app.modules.employees.router import router as employees_router
from app.modules.inventory.router import router as inventory_router
from app.modules.payslip.router import router as payslip_router
from app.routers import auth

# Built SPA assets, copied in by backend/Dockerfile (ADR-17: one origin).
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    yield
    engine.dispose()


app = FastAPI(
    title="SANGAD API",
    version="0.1.0",
    lifespan=lifespan,
)


def csrf_error_handler(request: Request, exc: CsrfError) -> JSONResponse:
    """In-app fallback: any handler raising CsrfError maps to a 403 problem
    response. CSRF middleware normally short-circuits before handlers run."""
    del request, exc
    return JSONResponse(
        status_code=403,
        content={
            "code": "csrf_failed",
            "detail": "CSRF token missing or invalid",
            "type": "about:blank",
        },
    )



# Host allowlist comes from settings. TrustedHost first so outer middleware
# already sees a validated Host header (middleware runs outermost-last added).
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://{host}" for host in settings.allowed_hosts],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["content-type", "x-csrf-token"],
    expose_headers=["content-type"],
)
# add_middleware wants Starlette's _MiddlewareFactory protocol; a
# BaseHTTPMiddleware subclass with extra kwargs satisfies it at runtime, so the
# cast surfaces that contract instead of widening add_middleware's signature.
_MW_FACTORY = cast(
    Any,
    RateLimitMiddleware,
)
app.add_middleware(_MW_FACTORY, max_requests=600, window_seconds=60)
app.add_middleware(CsrfMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
_exc_handler = cast(
    Callable[[Request, Exception], Response | Awaitable[Response]],
    csrf_error_handler,
)
app.add_exception_handler(AppError, cast(Any, app_error_handler))
app.add_exception_handler(CsrfError, _exc_handler)




@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness: the process is up. Never touches dependencies (K8s-style)."""
    return {"status": "ok"}


@app.get("/readyz")
def readyz(response: Response) -> dict[str, Any]:
    """Readiness: database, Redis and configured file storage answer.

    Any dependency failure returns 503 so the deploy is not declared healthy.
    """
    checks: dict[str, str] = {}
    status = 200
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            checks["database"] = "ok"
        finally:
            db.close()
    except Exception as exc:  # readiness reports the failure class
        checks["database"] = f"error: {type(exc).__name__}"
        status = 503

    try:
        pong = get_redis().ping()
        checks["redis"] = "ok" if pong else "error: no reply"
        if not pong:
            status = 503
    except Exception as exc:  # readiness reports the failure class
        checks["redis"] = f"error: {type(exc).__name__}"
        status = 503

    try:
        probe_storage()
        checks["storage"] = "ok"
    except Exception as exc:  # readiness reports the failure class
        checks["storage"] = f"error: {type(exc).__name__}"
        status = 503

    response.status_code = status
    state = "ok" if status == fastapi_status.HTTP_200_OK else "degraded"
    return {"status": state, "checks": checks}


@app.get("/api/v1/version")
def version(_user: Annotated[User, Depends(require_user)]) -> dict[str, str]:
    return {"version": "0.1.0"}


app.include_router(auth.router)
app.include_router(payslip_router)
app.include_router(bills_router)
app.include_router(inventory_router)
app.include_router(employees_router)
app.include_router(company_router)




# Mounted last so it never shadows the health routes or the /api/v1 routes.
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="spa")
