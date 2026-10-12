async def register(client, email, password="strong-password"):
    return await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
        },
    )


async def login(client, email, password="strong-password"):
    return await client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )


async def test_register_user(anonymous_client):

    response = await register(
        anonymous_client,
        "newuser@example.com",
    )

    assert response.status_code == 201

    data = response.json()

    assert "id" in data
    assert data["email"] == "newuser@example.com"
    assert "password" not in data
    assert "password_hash" not in data


async def test_duplicate_email_is_rejected(anonymous_client):

    email = "duplicate@example.com"

    first_response = await register(anonymous_client, email)

    assert first_response.status_code == 201

    second_response = await register(
        anonymous_client,
        email,
        "another-password",
    )

    assert second_response.status_code == 409


async def test_login_success(anonymous_client):

    email = "login@example.com"

    await register(anonymous_client, email)

    response = await login(anonymous_client, email)

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(anonymous_client):

    email = "wrong-password@example.com"

    await register(anonymous_client, email, "correct-password")

    response = await login(anonymous_client, email, "wrong-password")

    assert response.status_code == 401

    assert response.json()["detail"] == (
        "Invalid email or password."
    )


async def test_login_unknown_email(anonymous_client):

    response = await login(
        anonymous_client,
        "does-not-exist@example.com",
        "some-password",
    )

    assert response.status_code == 401

    assert response.json()["detail"] == (
        "Invalid email or password."
    )


async def test_me_requires_authentication(anonymous_client):

    response = await anonymous_client.get("/auth/me")

    assert response.status_code in {401, 403}


async def test_me_with_valid_token(anonymous_client):

    email = "me@example.com"

    await register(anonymous_client, email)

    login_response = await login(anonymous_client, email)

    token = login_response.json()["access_token"]

    response = await anonymous_client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 200
    assert response.json()["email"] == email


async def test_me_with_invalid_token(anonymous_client):

    response = await anonymous_client.get(
        "/auth/me",
        headers={
            "Authorization": "Bearer invalid-token"
        },
    )

    assert response.status_code == 401
