from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def get_auth_header():

    email = "interview-api@example.com"
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

    token = login_response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


def test_start_rejects_non_pdf():

    response = client.post(
        "/interview/start",
        files={
            "resume": (
                "resume.txt",
                b"hello",
                "text/plain",
            )
        },
        data={
            "job_description": "Python backend developer",
        },
        headers=get_auth_header(),
    )

    assert response.status_code == 400

    assert response.json()["detail"] == (
        "Invalid file type. Only PDF files are allowed."
    )