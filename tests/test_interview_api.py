from uuid import UUID

import pytest
from sqlalchemy import select

from app.models.interview import (
    InterviewAnswerModel,
    InterviewModel,
    InterviewStatus,
)
from app.models.user import UserModel
from app.routers import interview as interview_router
from app.schemas.interview import (
    Difficulty,
    InterviewQuestion,
    InterviewQuestionsResponse,
    QuestionCategory,
)
from app.services.exceptions import AIServiceUnavailableError


@pytest.mark.asyncio
async def test_start_rejects_non_pdf(
    client,
    monkeypatch,
):
    def should_not_parse(content: bytes) -> str:
        raise AssertionError(
            "PDF parser should not run for a non-PDF upload."
        )

    monkeypatch.setattr(
        interview_router,
        "extract_text_from_pdf",
        should_not_parse,
    )

    response = await client.post(
        "/interview/start",
        files={
            "resume": (
                "resume.txt",
                b"not a PDF",
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


def make_five_questions() -> InterviewQuestionsResponse:
    return InterviewQuestionsResponse(
        questions=[
            InterviewQuestion(
                id=1,
                question="Explain dependency injection in FastAPI.",
                category=QuestionCategory.TECHNICAL,
                difficulty=Difficulty.MEDIUM,
                expected_topics=["Depends", "dependencies"],
            ),
            InterviewQuestion(
                id=2,
                question="Explain asynchronous programming in Python.",
                category=QuestionCategory.TECHNICAL,
                difficulty=Difficulty.MEDIUM,
                expected_topics=["async", "await"],
            ),
            InterviewQuestion(
                id=3,
                question="Describe a challenging project you completed.",
                category=QuestionCategory.BEHAVIORAL,
                difficulty=Difficulty.MEDIUM,
                expected_topics=["challenge", "solution"],
            ),
            InterviewQuestion(
                id=4,
                question="How would you debug a production issue?",
                category=QuestionCategory.PROBLEM_SOLVING,
                difficulty=Difficulty.HARD,
                expected_topics=["logs", "diagnosis"],
            ),
            InterviewQuestion(
                id=5,
                question="Explain the design of a backend system.",
                category=QuestionCategory.SYSTEM_DESIGN,
                difficulty=Difficulty.HARD,
                expected_topics=["architecture", "tradeoffs"],
            ),
        ]
    )


@pytest.mark.asyncio
async def test_start_interview_saves_to_database(
    client,
    test_session,
    monkeypatch,
):
    async def fake_generate_questions(
        resume_text: str,
        job_description: str,
    ) -> InterviewQuestionsResponse:
        assert resume_text == "Extracted test resume."
        assert job_description == "Python backend developer"

        return make_five_questions()

    monkeypatch.setattr(
        interview_router,
        "extract_text_from_pdf",
        lambda content: "Extracted test resume.",
    )

    monkeypatch.setattr(
        interview_router,
        "generate_interview_questions",
        fake_generate_questions,
    )

    response = await client.post(
        "/interview/start",
        files={
            "resume": (
                "resume.pdf",
                b"fake PDF bytes",
                "application/pdf",
            )
        },
        data={
            "job_description": "Python backend developer",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert len(data["questions"]) == 5
    assert "interview_id" in data

    interview_id = UUID(data["interview_id"])

    result = await test_session.execute(
        select(InterviewModel).where(
            InterviewModel.id == interview_id
        )
    )

    interview = result.scalar_one()

    assert interview.resume_text == "Extracted test resume."
    assert interview.job_description == "Python backend developer"
    assert len(interview.questions) == 5


@pytest.mark.asyncio
async def test_ai_failure_does_not_create_interview(
    client,
    test_session,
    monkeypatch,
):
    async def fake_generate_questions(
        resume_text: str,
        job_description: str,
    ):
        raise AIServiceUnavailableError(
            "Simulated provider failure."
        )

    monkeypatch.setattr(
        interview_router,
        "extract_text_from_pdf",
        lambda content: "Extracted test resume.",
    )

    monkeypatch.setattr(
        interview_router,
        "generate_interview_questions",
        fake_generate_questions,
    )

    response = await client.post(
        "/interview/start",
        files={
            "resume": (
                "resume.pdf",
                b"fake PDF bytes",
                "application/pdf",
            )
        },
        data={
            "job_description": "Python backend developer",
        },
    )

    assert response.status_code == 503

    result = await test_session.execute(
        select(InterviewModel)
    )

    assert result.scalars().all() == []

@pytest.mark.asyncio
async def test_submit_answer_persists_to_database(
    client,
    test_session,
    test_user_id,
):
    interview = InterviewModel(
        user_id=test_user_id,
        resume_text="Python developer.",
        job_description="Python backend developer.",
        questions=[
            {
                "id": 1,
                "question": "Explain dependency injection in FastAPI.",
                "category": "technical",
                "difficulty": "medium",
                "expected_topics": ["Depends"],
            }
        ],
        status=InterviewStatus.IN_PROGRESS,
    )

    test_session.add(interview)
    await test_session.commit()
    await test_session.refresh(interview)

    response = await client.post(
        f"/interview/{interview.id}/answers",
        json={
            "question_id": 1,
            "answer": "FastAPI uses Depends for dependency injection.",
        },
    )

    assert response.status_code == 200

    result = await test_session.execute(
        select(InterviewAnswerModel).where(
            InterviewAnswerModel.interview_id == interview.id,
            InterviewAnswerModel.question_id == 1,
        )
    )

    saved_answer = result.scalar_one()

    assert saved_answer.answer == (
        "FastAPI uses Depends for dependency injection."
    )


@pytest.mark.asyncio
async def test_list_interviews_returns_only_current_user_interviews(
    client,
    test_session,
    test_user_id,
):
    other_user = UserModel(
        email="other-user@example.com",
        password_hash="$2b$12$test-placeholder",
    )
    test_session.add(other_user)
    await test_session.commit()
    await test_session.refresh(other_user)

    question = {
        "id": 1,
        "question": "Explain dependency injection in FastAPI.",
        "category": "technical",
        "difficulty": "medium",
        "expected_topics": ["Depends"],
    }

    own_interview = InterviewModel(
        user_id=test_user_id,
        resume_text="Python developer.",
        job_description="Python backend developer.",
        questions=[question],
        status=InterviewStatus.IN_PROGRESS,
    )
    other_interview = InterviewModel(
        user_id=other_user.id,
        resume_text="Java developer.",
        job_description="Java backend developer.",
        questions=[question],
        status=InterviewStatus.IN_PROGRESS,
    )

    test_session.add_all([own_interview, other_interview])
    await test_session.commit()
    await test_session.refresh(own_interview)

    test_session.add(
        InterviewAnswerModel(
            interview_id=own_interview.id,
            question_id=1,
            answer="FastAPI uses Depends.",
        )
    )
    await test_session.commit()

    response = await client.get("/interview")

    assert response.status_code == 200

    body = response.json()

    assert len(body) == 1
    assert body[0]["interview_id"] == str(own_interview.id)
    assert body[0]["status"] == "in_progress"
    assert body[0]["total_questions"] == 1
    assert body[0]["answered_questions"] == 1
    assert body[0]["overall_score"] is None
