"""Kernel auth: login + email OTP + sessions (T-004).

Implements F-AUTH-01..05 and is verified by V-AUTH-01..06:
  - V-AUTH-01  correct password alone never creates a session
  - V-AUTH-02  expired, reused or 6th-attempt OTP is rejected
  - V-AUTH-03  password change requires an OTP (purpose=password_change)
  - V-AUTH-04  N failed logins lock the account for a configured window (Redis)
  - V-AUTH-05  (frontend) username + role shown in the top bar
  - V-AUTH-06  no API route except login/OTP/health answers without a session
"""
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from fastapi import Request
from sqlalchemy.orm import Session as DbSession

from app.core.config import settings
from app.core.errors import AppError
from app.core.passwords import hash_password, verify_password
from app.kernel import models
from app.kernel.jobs import get_redis, redis_exists, redis_incr, redis_ttl
from app.kernel.mail import send_email

# --- tunables -----------------------------------------------------------------
# The policy values an operator can change live in Settings (R-17): OTP
# expiry and attempts, session idle and absolute lifetime, and the login
# lockout threshold and window. They are read through `settings` at the
# point of use so a configuration change takes effect without a code edit.
#
# The constants below are fixed protocol rules that no deployment should
# change: the OTP digit count, the resend cooldown, and the password
# minimum length.
OTP_LENGTH: Final[int] = 6
OTP_RESEND_COOLDOWN_SECONDS: Final[int] = 60  # F-AUTH-02
PASSWORD_MIN_LENGTH: Final[int] = 8

# Redis key namespaces. Every value carries its own TTL.
_FAIL_KEY: Final[str] = "sangad:loginfail:{username}"
_LOCK_KEY: Final[str] = "sangad:lockout:{username}"


def _cooldown_key(user_id: str, purpose: str) -> str:
    return f"sangad:otpcooldown:{user_id}:{purpose}"


def _random_token() -> str:
    return secrets.token_urlsafe(48)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _hash_otp(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _generate_otp() -> str:
    return f"{secrets.randbelow(10**OTP_LENGTH):0{OTP_LENGTH}d}"


def _now() -> datetime:
    return datetime.now(UTC)


# --- Redis-backed lockout (V-AUTH-04) ----------------------------------------


def _lock_key(username: str) -> str:
    return _LOCK_KEY.format(username=username.lower())


def is_locked(username: str) -> bool:
    return redis_exists(_lock_key(username))


def lock_ttl_seconds(username: str) -> int:
    return max(0, redis_ttl(_lock_key(username)))


def record_login_failure(username: str) -> int:
    """Count one failure; lock the account when the limit is reached."""
    key = _FAIL_KEY.format(username=username.lower())
    count = redis_incr(key)
    if count == 1:
        get_redis().expire(key, settings.login_lockout_minutes * 60)
    if count >= settings.login_failure_limit:
        get_redis().set(_lock_key(username), "1", ex=settings.login_lockout_minutes * 60)
        get_redis().delete(key)
    return count


def clear_login_failures(username: str) -> None:
    get_redis().delete(_FAIL_KEY.format(username=username.lower()))


# --- OTP issue / verify (F-AUTH-02, V-AUTH-02) --------------------------------


def _latest_open_challenge(
    db: DbSession, user_id: str, purpose: str
) -> models.OtpChallenge | None:
    return (
        db.query(models.OtpChallenge)
        .filter(
            models.OtpChallenge.user_id == user_id,
            models.OtpChallenge.purpose == purpose,
            models.OtpChallenge.consumed_at.is_(None),
            models.OtpChallenge.expires_at > _now(),
        )
        .order_by(models.OtpChallenge.created_at.desc())
        .first()
    )


def issue_otp(db: DbSession, user: models.User, purpose: str) -> None:
    """Generate a hashed single-use OTP, persist it, email it.

    The code itself is never returned to the caller and never logged. If the
    mail send fails the challenge is revoked immediately so a broken mail
    server can never turn into an OTP oracle.
    """
    r = get_redis()
    key = _cooldown_key(str(user.id), purpose)
    if redis_exists(key):
        raise AppError(
            429,
            "otp_cooldown",
            f"Wait {OTP_RESEND_COOLDOWN_SECONDS}s before requesting another code",
        )

    otp = _generate_otp()
    challenge = models.OtpChallenge(
        user_id=user.id,
        purpose=purpose,
        code_hash=_hash_otp(otp),
        expires_at=_now() + timedelta(minutes=settings.otp_expiry_minutes),
    )
    db.add(challenge)
    db.commit()
    r.set(key, "1", ex=OTP_RESEND_COOLDOWN_SECONDS)

    sent = send_email(
        str(user.email),
        "Your SANGAD verification code",
        f"Your verification code is: {otp}\nExpires in {settings.otp_expiry_minutes} minutes.",
    )
    if not sent:
        challenge.consumed_at = _now()
        db.commit()
        raise AppError(502, "mail_failure", "Could not send the verification email")


# --- login flow (V-AUTH-01, V-AUTH-04) ----------------------------------------


def initiate_login(db: DbSession, username: str, password: str, _ip: str) -> dict[str, Any]:
    """Password check only; a session can only ever be created by verify_otp."""
    if is_locked(username):
        ttl = lock_ttl_seconds(username)
        raise AppError(
            423,
            "account_locked",
            f"Account locked after too many failed attempts. Try again in {ttl}s.",
        )

    user = db.query(models.User).filter(models.User.username == username).first()
    # Same error for unknown user and wrong password, so probing usernames via
    # the OTP-mail side channel learns nothing.
    if not user or not user.is_active or not verify_password(password, str(user.password_hash)):
        record_login_failure(username)
        if is_locked(username):
            raise AppError(
                423,
                "account_locked",
                f"Account locked for {settings.login_lockout_minutes} minutes after "
                f"{settings.login_failure_limit} failed attempts.",
            )
        raise AppError(401, "invalid_credentials", "Invalid username or password")

    clear_login_failures(username)
    issue_otp(db, user, "login")
    return {"message": "verification code sent to the registered email"}


def verify_otp(db: DbSession, username: str, otp: str, ip: str) -> dict[str, Any]:
    """Consume the open login challenge and mint the session (V-AUTH-02)."""
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not user.is_active:
        raise AppError(401, "invalid_credentials", "Invalid username or password")

    challenge = _latest_open_challenge(db, str(user.id), "login")
    if not challenge:
        raise AppError(401, "otp_expired", "Code expired or not requested")

    if challenge.attempts >= settings.otp_max_attempts:
        challenge.consumed_at = _now()
        db.commit()
        raise AppError(401, "otp_locked", "Too many incorrect codes; request a new one")

    challenge.attempts += 1
    if not hmac.compare_digest(str(challenge.code_hash), _hash_otp(otp)):
        db.commit()
        raise AppError(401, "invalid_otp", "Invalid code")
    challenge.consumed_at = _now()

    token = _random_token()
    session = models.Session(
        user_id=user.id,
        token_hash=_hash_token(token),
        ip_address=ip,
        last_activity=_now(),
        expires_at=_now() + timedelta(hours=settings.session_absolute_hours),
    )
    db.add(session)
    db.flush()
    db.add(
        models.AuditLog(
            actor=str(user.username),
            action="login",
            entity="session",
            entity_id=session.id,
            ip_address=ip,
        )
    )
    db.commit()
    return {"token": token, "user": {"username": user.username, "role": user.role}}


# --- sessions (V-AUTH-06) ----------------------------------------------------


def get_current_session(
    db: DbSession, request: Request
) -> tuple[models.User, models.Session]:
    """Resolve the session cookie (Authorization: Bearer for tests/CLI only)."""
    token = request.cookies.get("session")
    if not token:
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
    if not token:
        raise AppError(401, "unauthorized", "Session required")

    row = db.query(models.Session).filter(
        models.Session.token_hash == _hash_token(token)
    ).first()
    if not row or row.expires_at <= _now():
        raise AppError(401, "session_expired", "Invalid or expired session")

    idle_cutoff = _now() - timedelta(minutes=settings.session_idle_minutes)
    if row.last_activity < idle_cutoff:
        db.delete(row)
        db.commit()
        raise AppError(401, "session_expired", "Session expired after inactivity")

    user = db.query(models.User).filter(models.User.id == row.user_id).first()
    if not user or not user.is_active:
        raise AppError(401, "user_inactive", "User not found or inactive")

    row.last_activity = _now()
    db.commit()
    return user, row


def logout(db: DbSession, token: str) -> None:
    db.query(models.Session).filter(models.Session.token_hash == _hash_token(token)).delete()
    db.commit()


# --- password change (F-AUTH-03, V-AUTH-03) -----------------------------------


def request_password_change_otp(db: DbSession, user: models.User, _ip: str) -> dict[str, Any]:
    """F-AUTH-03 step 1: email an OTP with purpose=password_change."""
    issue_otp(db, user, "password_change")
    return {"message": "verification code sent to the registered email"}


def change_password(  # noqa: PLR0913 - coordinates from one request envelope
    db: DbSession,
    user: models.User,
    *,
    current_password: str,
    new_password: str,
    otp: str,
    ip: str,
) -> dict[str, Any]:
    """F-AUTH-03 step 2: current password + fresh OTP -> new password."""
    if not verify_password(current_password, str(user.password_hash)):
        raise AppError(401, "invalid_password", "Current password is incorrect")
    if len(new_password) < PASSWORD_MIN_LENGTH:
        raise AppError(
            422, "weak_password", f"Password must be at least {PASSWORD_MIN_LENGTH} characters"
        )

    challenge = _latest_open_challenge(db, str(user.id), "password_change")
    if not challenge:
        raise AppError(
            403, "otp_required", "Verify the emailed code before changing the password"
        )
    if challenge.attempts >= settings.otp_max_attempts:
        challenge.consumed_at = _now()
        db.commit()
        raise AppError(401, "otp_locked", "Too many incorrect codes; request a new one")

    challenge.attempts += 1
    if not hmac.compare_digest(str(challenge.code_hash), _hash_otp(otp)):
        db.commit()
        raise AppError(401, "invalid_otp", "Invalid code")
    challenge.consumed_at = _now()

    user.password_hash = hash_password(new_password)
    db.add(
        models.AuditLog(
            actor=str(user.username),
            action="password_change",
            entity="user",
            entity_id=user.id,
            ip_address=ip,
        )
    )
    db.commit()
    return {"message": "Password changed successfully"}
