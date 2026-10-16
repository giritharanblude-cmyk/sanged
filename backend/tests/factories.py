"""Test factories: real users/hashes, no mocks of business behaviour."""
from sqlalchemy.orm import Session

from app.core.passwords import hash_password
from app.kernel import models

TEST_PASSWORD = "correct-horse-1"


def make_user(
    db: Session,
    username: str = "admin",
    password: str = TEST_PASSWORD,
    email: str | None = None,
) -> tuple[models.User, str]:
    user = models.User(
        username=username,
        email=email or f"{username}@sangad.localhost",
        password_hash=hash_password(password),
        role="master",
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user, password
