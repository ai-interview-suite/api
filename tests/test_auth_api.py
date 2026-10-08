from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)

def test_register_user():

    response = client.post(
        "/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "strong-password",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "id" in data
    assert data["email"] == "newuser@example.com"
    assert "password" not in data
    assert "password_hash" not in data

def test_duplicate_email_is_rejected():

    email = "duplicate@example.com"

    first_response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "strong-password",
        },
    )

    assert first_response.status_code == 200

    second_response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "another-password",
        },
    )

    assert second_response.status_code == 409

def test_login_success():

    email = "login@example.com"
    password = "strong-password"

    client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
        },
    )

    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_wrong_password():

    email = "wrong-password@example.com"

    client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "correct-password",
        },
    )

    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401

    assert response.json()["detail"] == (
        "Invalid email or password."
    )

def test_login_unknown_email():

    response = client.post(
        "/auth/login",
        json={
            "email": "does-not-exist@example.com",
            "password": "some-password",
        },
    )

    assert response.status_code == 401

    assert response.json()["detail"] == (
        "Invalid email or password."
    )

def test_me_requires_authentication():

    response = client.get(
        "/auth/me"
    )

    assert response.status_code in {401, 403}

def test_me_with_valid_token():

    email = "me@example.com"
    password = "strong-password"

    client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
        },
    )

    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    token = login_response.json()[
        "access_token"
    ]

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 200
    assert response.json()["email"] == email

def test_me_with_invalid_token():

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": "Bearer invalid-token"
        },
    )

    assert response.status_code == 401