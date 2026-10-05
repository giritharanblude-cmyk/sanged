"""Bootstrap the first admin user.

No migration seeds any user, so without this the OTP login flow has nothing to
authenticate against. Idempotent: exits quietly if a user already exists.

    docker compose run --rm api python -m app.seed
"""

import logging
import sys

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.kernel.models import User

logger = logging.getLogger(__name__)


def main() -> int:
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == settings.admin_username).first()
        if existing:
            logger.info("user %r already exists, nothing to do", settings.admin_username)
            return 0

        if not settings.admin_password:
            logger.error(
                "ADMIN_PASSWORD is not set; refusing to create a user with an "
                "unusable password. Set ADMIN_PASSWORD and retry."
            )
            return 1

        user = User(
            username=settings.admin_username,
            email=settings.admin_email,
            password_hash=hash_password(settings.admin_password),
            role="master",
            is_active=True,
        )
        db.add(user)
        db.commit()
        logger.info("created admin user %r (%s)", user.username, user.email)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())