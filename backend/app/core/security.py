from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()

_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False
    return True


async def require_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),  # noqa: B008
) -> str:
    """Stub — returns user id from session. Wired properly in T-004."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return "stub-user-id"
