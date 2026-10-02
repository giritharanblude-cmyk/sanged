from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.core.app_logging import setup_logging
from app.core.errors import AppError, app_error_handler
from app.core.middleware import RateLimitMiddleware, SecurityHeadersMiddleware
from app.routers import auth
from app.modules.payslip.router import router as payslip_router
from app.modules.bills.router import router as bills_router
from app.modules.inventory.router import router as inventory_router
from app.modules.employees.router import router as employees_router
from app.modules.company.router import router as company_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    yield


app = FastAPI(title="SANGAD API", version="0.1.0", lifespan=lifespan)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)
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
    return {"status": "ok", "db": True, "redis": True}


@app.get("/api/v1/version")
async def version() -> dict[str, Any]:
    return {"version": "0.1.0", "build": "T-701"}