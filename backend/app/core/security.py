"""Session/CSRF helpers (T-004, T-009); password hashing lives in core.passwords."""
import secrets
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session as DbSession

from app.core.config import settings
from app.core.db import get_db
from app.core.passwords import hash_password, verify_password  # noqa: F401 (public API)
from app.kernel import models
from app.kernel.auth import get_current_session

CSRF_COOKIE: str = "csrf_token"
CSRF_HEADER: str = "x-csrf-token"
CSRF_SAFE_METHODS: frozenset[str] = frozenset({"GET", "HEAD", "OPTIONS"})


class CsrfError(Exception):
    """Raised when a mutating request fails the CSRF double-submit check."""


def cookie_params() -> dict[str, object]:
    """Attributes for the session cookie, driven by the environment.

    COOKIE_SECURE=true in any non-local environment so the browser only ever
    sends the session over TLS (C-12: plaintext loopback is local-only).
    """
    return {
        "httponly": True,
        "samesite": "strict",
        "secure": settings.cookie_secure,
        "path": "/",
    }


def new_csrf_token() -> str:
    """Random token issued at login and echoed by every unsafe request."""
    return secrets.token_urlsafe(24)


def require_user(
    request: Request,
    db: Annotated[DbSession, Depends(get_db)],
) -> models.User:
    """Dependency for every protected endpoint (V-AUTH-06)."""
    user, _session = get_current_session(db, request)
    return user


def assert_csrf(request: Request) -> None:
    """Double-submit CSRF check for unsafe methods (T-701 OWASP review).

    The cookie is issued alongside the session at login; JS clients echo it in
    the x-csrf-token header. A cross-site attacker can make the browser send
    the cookie but cannot read it (httpOnly) so cannot set the header.
    """
    if request.method in CSRF_SAFE_METHODS:
        return
    cookie_token = request.cookies.get(CSRF_COOKIE, "")
    header_token = request.headers.get(CSRF_HEADER, "")
    if not cookie_token or not header_token or not secrets.compare_digest(
        cookie_token, header_token
    ):
        raise CsrfError("CSRF token missing or invalid")
