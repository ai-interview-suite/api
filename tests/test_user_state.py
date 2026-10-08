from app.services.password import hash_password
from app.services.user_state import (
    create_user,
    get_user_by_email,
    get_user_by_id,
)


def test_create_user():

    user = create_user(
        email="alice@example.com",
        password_hash=hash_password(
            "password123"
        ),
    )

    assert user.email == "alice@example.com"
    assert user.password_hash != "password123"


def test_find_user_by_email():

    user = create_user(
        email="bob@example.com",
        password_hash=hash_password(
            "password123"
        ),
    )

    found = get_user_by_email(
        "bob@example.com"
    )

    assert found is not None
    assert found.id == user.id


def test_find_user_by_id():

    user = create_user(
        email="charlie@example.com",
        password_hash=hash_password(
            "password123"
        ),
    )

    found = get_user_by_id(user.id)

    assert found is not None
    assert found.email == "charlie@example.com"