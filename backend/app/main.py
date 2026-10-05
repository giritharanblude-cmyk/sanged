from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.db import engine
from app.core.errors import AppError, app_error_handler
from app.core.logging import setup_logging
from app.core.middleware import RateLimitMiddleware, SecurityHeadersMiddleware
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

# Host allowlist comes from settings, never a wildcard: the ported phase-3
# main.py hard-coded "*", which would undo the ALLOWED_HOSTS fix.
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://{host}" for host in settings.allowed_hosts],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware, max_requests=600, window_seconds=60)
app.add_middleware(SecurityHeadersMiddleware)
app.add_exception_handler(AppError, app_error_handler)

app.include_router(auth.router)
app.include_router(payslip_router)
app.include_router(bills_router)
app.include_router(inventory_router)
app.include_router(employees_router)
app.include_router(company_router)


@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict[str, Any]:
    return {"status": "ok"}


@app.get("/api/v1/version")
async def version() -> dict[str, Any]:
    return {"version": "0.1.0"}


# Mounted last so it never shadows the health routes or the /api/v1 routes.
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="spa")