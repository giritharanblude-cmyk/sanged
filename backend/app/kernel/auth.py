import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import Depends, Request
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session as DbSession

from app.core.db import get_db
from app.core.errors import AppError
from app.kernel import models


def _random_token() -> str:
    return secrets.token_urlsafe(48)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _hash_otp(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _generate_otp() -> str:
    return f"{secrets.randbelow(1000000):06d}"


bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    db: DbSession = Depends(get_db),
) -> models.User:
    token = request.cookies.get("session")
    if not token:
        creds = await bearer_scheme(request)
        if creds is None:
            raise AppError(401, "unauthorized", "Session required")
        token = creds.credentials
    token_hash = _hash_token(token)
    session = (
        db.query(models.Session)
        .filter(
            models.Session.token_hash == token_hash,
            models.Session.expires_at > datetime.now(UTC),
        )
        .first()
    )
    if not session:
        raise AppError(401, "session_expired", "Invalid or expired session")
    session.last_activity = datetime.now(UTC)
    db.commit()
    user = db.query(models.User).filter(models.User.id == session.user_id).first()
    if not user or not user.is_active:
        raise AppError(401, "user_inactive", "User not found or inactive")
    return user


def initiate_login(db: DbSession, username: str, ip: str) -> dict:
    user = (
        db.query(models.User)
        .filter(models.User.username == username, models.User.is_active)
        .first()
    )
    if not user:
        raise AppError(401, "invalid_credentials", "Invalid username or password")
    otp = _generate_otp()
    challenge = models.OtpChallenge(
        user_id=user.id,
        purpose="login",
        code_hash=_hash_otp(otp),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    db.add(challenge)
    db.commit()
    from app.kernel.mail import send_email

    send_email(user.email, "Your SANGAD OTP", f"Your OTP is: {otp}\nExpires in 5 minutes.")
    return {"message": "OTP sent to registered email"}


def verify_otp(db: DbSession, username: str, otp: str, ip: str) -> dict:
    user = (
        db.query(models.User)
        .filter(models.User.username == username, models.User.is_active)
        .first()
    )
    if not user:
        raise AppError(401, "invalid_credentials", "Invalid username or password")
    challenge = (
        db.query(models.OtpChallenge)
        .filter(
            models.OtpChallenge.user_id == user.id,
            models.OtpChallenge.purpose == "login",
            models.OtpChallenge.consumed_at.is_(None),
            models.OtpChallenge.expires_at > datetime.now(UTC),
        )
        .order_by(models.OtpChallenge.created_at.desc())
        .first()
    )
    if not challenge:
        raise AppError(401, "otp_expired", "OTP expired or not requested")
    if challenge.attempts >= 5:
        challenge.consumed_at = datetime.now(UTC)
        db.commit()
        raise AppError(429, "otp_locked", "Too many OTP attempts")
    challenge.attempts += 1
    if not hmac.compare_digest(challenge.code_hash, _hash_otp(otp)):
        db.commit()
        raise AppError(401, "invalid_otp", "Invalid OTP")
    challenge.consumed_at = datetime.now(UTC)
    token = _random_token()
    token_hash = _hash_token(token)
    session = models.Session(
        user_id=user.id,
        token_hash=token_hash,
        ip_address=ip,
        last_activity=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=12),
    )
    db.add(session)
    audit = models.AuditLog(
        actor=user.username, action="login", entity="session", entity_id=session.id, ip_address=ip
    )
    db.add(audit)
    db.commit()
    return {"token": token, "user": {"username": user.username, "role": user.role}}


def logout(db: DbSession, token: str) -> None:
    token_hash = _hash_token(token)
    session = db.query(models.Session).filter(models.Session.token_hash == token_hash).first()
    if session:
        db.delete(session)
        db.commit()


def change_password(
    db: DbSession, user: models.User, current_password: str, new_password: str, ip: str
) -> dict:
    from app.core.security import hash_password, verify_password

    if not verify_password(current_password, user.password_hash):
        raise AppError(401, "invalid_password", "Current password is incorrect")
    user.password_hash = hash_password(new_password)
    audit = models.AuditLog(
        actor=user.username,
        action="password_change",
        entity="user",
        entity_id=user.id,
        ip_address=ip,
    )
    db.add(audit)
    db.commit()
    return {"message": "Password changed successfully"}
