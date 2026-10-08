from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import jwt

from app.config import settings


def create_access_token(
    user_id: UUID,
) -> str:

    expires_at = (
        datetime.now(timezone.utc)
        + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    )

    payload = {
        "sub": str(user_id),
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )