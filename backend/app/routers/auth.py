from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession

from app.core.db import get_db
from app.kernel.auth import change_password, get_current_user, initiate_login, logout, verify_otp
from app.kernel.models import User

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class OtpVerifyRequest(BaseModel):
    username: str = Field(min_length=1)
    otp: str = Field(min_length=6, max_length=6)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


def _ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


@router.post("/login")
def login(req: LoginRequest, request: Request, db: DbSession = Depends(get_db)):
    return initiate_login(db, req.username, _ip(request))


@router.post("/verify-otp")
def verify_otp_endpoint(
    req: OtpVerifyRequest, request: Request, response: Response, db: DbSession = Depends(get_db)
):
    result = verify_otp(db, req.username, req.otp, _ip(request))
    response.set_cookie(
        key="session",
        value=result["token"],
        httponly=True,
        samesite="strict",
        secure=False,
        max_age=43200,
    )
    return {"user": result["user"], "message": "Login successful"}


@router.post("/logout")
def logout_endpoint(request: Request, response: Response, db: DbSession = Depends(get_db)):
    token = request.cookies.get("session")
    if token:
        logout(db, token)
    response.delete_cookie("session")
    return {"message": "Logged out"}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"username": user.username, "role": user.role}


@router.post("/change-password")
def change_password_endpoint(
    req: PasswordChangeRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    return change_password(db, user, req.current_password, req.new_password, _ip(request))
