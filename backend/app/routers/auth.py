"""Auth API: login -> OTP -> session cookie, /me, logout, password change.

The OTP email itself is sent by app.kernel.auth; this layer only handles HTTP
shape: pydantic validation, cookies, CSRF tokens, status codes.
"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession

from app.core.config import settings
from app.core.db import get_db
from app.core.security import (
    CSRF_COOKIE,
    cookie_params,
    new_csrf_token,
    require_user,
)
from app.kernel import models
from app.kernel.auth import (
    change_password,
    initiate_login,
    logout,
    request_password_change_otp,
    verify_otp,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_db_dep: Annotated[DbSession, Depends(get_db)] = Depends(get_db)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class OtpVerifyRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=8, max_length=200)
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


@router.post("/login")
def login(
    req: LoginRequest, request: Request, db: Annotated[DbSession, Depends(get_db)]
) -> dict[str, str]:
    """Step 1 (F-AUTH-01): verify credentials, email an OTP. No session is created
    here (V-AUTH-01)."""
    return initiate_login(db, req.username, req.password, _client_ip(request))


@router.post("/verify-otp")
def verify_otp_endpoint(
    req: OtpVerifyRequest,
    request: Request,
    response: Response,
    db: Annotated[DbSession, Depends(get_db)],
) -> dict[str, Any]:
    """Step 2 (F-AUTH-01): consume the OTP, create the session cookie (V-AUTH-02)."""
    result = verify_otp(db, req.username, req.otp, _client_ip(request))
    params = cookie_params()
    response.set_cookie(
        key="session",
        value=str(result["token"]),
        max_age=settings.session_absolute_hours * 3600,
        path=str(params["path"]),
        httponly=True,
        samesite="strict",
        secure=settings.cookie_secure,
    )
    csrf = new_csrf_token()
    response.set_cookie(
        key=CSRF_COOKIE,
        value=csrf,
        max_age=settings.session_lifetime_seconds(),
        httponly=False,  # JS must read it to echo it back
        samesite="strict",
        secure=settings.cookie_secure,
        path="/",
    )
    user = result["user"]
    return {"user": user, "message": "Login successful"}


@router.post("/logout")
def logout_endpoint(
    request: Request,
    response: Response,
    _user: Annotated[models.User, Depends(require_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> dict[str, str]:
    """Sign out: delete the server-side session row (F-AUTH-05)."""
    token = request.cookies.get("session")
    if token:
        logout(db, token)
    response.delete_cookie("session", path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return {"message": "Logged out"}


@router.get("/me")
def me(user: Annotated[models.User, Depends(require_user)]) -> dict[str, str]:
    """F-AUTH-04: the shell renders username and role from this."""
    return {"username": user.username, "role": user.role}


@router.post("/change-password/init")
def change_password_init(
    request: Request,
    user: Annotated[models.User, Depends(require_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> dict[str, str]:
    """F-AUTH-03 step 1 (V-AUTH-03): email an OTP to the authenticated user."""
    return request_password_change_otp(db, user, _client_ip(request))


@router.post("/change-password")
def change_password_endpoint(
    request: Request,
    user: Annotated[models.User, Depends(require_user)],
    db: Annotated[DbSession, Depends(get_db)],
    req: PasswordChangeRequest,
) -> dict[str, str]:
    """F-AUTH-03 step 2 (V-AUTH-03): current password + fresh OTP -> new password."""
    return change_password(
        db,
        user,
        current_password=req.current_password,
        new_password=req.new_password,
        otp=req.otp,
        ip=_client_ip(request),
    )
