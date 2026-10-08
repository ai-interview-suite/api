from uuid import uuid4

from jose import jwt

from app.config import settings
from app.services.auth import create_access_token


def test_create_access_token():

    user_id = uuid4()

    token = create_access_token(
        user_id
    )

    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )

    assert payload["sub"] == str(user_id)
    assert "exp" in payload