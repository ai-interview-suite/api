from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

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
    )

    assert response.status_code == 400

    assert response.json()["detail"] == (
        "Invalid file type. Only PDF files are allowed."
    )