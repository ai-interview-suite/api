from app.services.password import (
    hash_password,
    verify_password,
)


def test_password_is_hashed():

    password = "my-secret-password"

    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$2")


def test_correct_password_is_valid():

    password = "my-secret-password"

    hashed = hash_password(password)

    assert verify_password(
        password,
        hashed,
    )


def test_wrong_password_is_invalid():

    password = "my-secret-password"

    hashed = hash_password(password)

    assert not verify_password(
        "wrong-password",
        hashed,
    )

def test_same_password_gets_different_hashes():

    password = "my-secret-password"

    hash_one = hash_password(password)
    hash_two = hash_password(password)

    assert hash_one != hash_two

    assert verify_password(
        password,
        hash_one,
    )

    assert verify_password(
        password,
        hash_two,
    )