from uuid import UUID

import pytest
from sqlalchemy import select

from app.models.answer import AnswerModel
from app.models.answer_evaluation import AnswerEvaluationModel
from app.models.interview import InterviewModel
from app.models.interview_attempt import (
    InterviewAttemptModel,
    InterviewStatus,
)
from app.models.question import QuestionModel
from app.models.user import UserModel
from app.repositories.interview_repository import create_interview
from app.routers import interview as interview_router
from app.schemas.interview import (
    AnswerEvaluation,
    Difficulty,
    InterviewEvaluationResponse,
    InterviewQuestion,
    InterviewQuestionsResponse,
    QuestionCategory,
)
from app.services import interview_completion
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
            InterviewModel.interview_id == interview_id
        )
    )

    interview = result.scalar_one()

    assert interview.resume_text == "Extracted test resume."
    assert interview.job_description == "Python backend developer"

    attempt = (
        await test_session.execute(
            select(InterviewAttemptModel).where(
                InterviewAttemptModel.interview_id == interview_id
            )
        )
    ).scalar_one()

    assert attempt.attempt_number == 1
    assert attempt.status == InterviewStatus.IN_PROGRESS

    positions = (
        await test_session.execute(
            select(QuestionModel.position)
            .where(
                QuestionModel.interview_attempt_id
                == attempt.interview_attempt_id
            )
            .order_by(QuestionModel.position)
        )
    ).scalars().all()

    assert positions == [1, 2, 3, 4, 5]


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

    result = await test_session.execute(
        select(InterviewAttemptModel)
    )

    assert result.scalars().all() == []

async def create_test_interview(
    session,
    user_id: UUID,
    question_count: int = 5,
) -> InterviewModel:
    return await create_interview(
        db=session,
        user_id=user_id,
        resume_text="Python developer.",
        job_description="Python backend developer.",
        questions=make_five_questions().questions[:question_count],
    )


async def get_saved_answers(session, interview_id: UUID) -> dict[int, str]:
    result = await session.execute(
        select(QuestionModel.position, AnswerModel.answer)
        .join(AnswerModel.question)
        .join(QuestionModel.interview_attempt)
        .where(InterviewAttemptModel.interview_id == interview_id)
    )

    return dict(result.all())


def make_evaluations(question_ids: list[int]) -> InterviewEvaluationResponse:
    return InterviewEvaluationResponse.model_construct(
        evaluations=[
            AnswerEvaluation(
                question_id=question_id,
                technical_accuracy=8,
                relevance=7,
                completeness=6,
                communication=9,
                evidence=[f"Evidence {question_id}"],
                strengths=[f"Strength {question_id}"],
                weaknesses=[f"Weakness {question_id}"],
                feedback=f"Feedback for answer {question_id}.",
            )
            for question_id in question_ids
        ]
    )


@pytest.mark.asyncio
async def test_submit_answer_persists_to_database(
    client,
    test_session,
    test_user_id,
):
    interview = await create_test_interview(
        test_session,
        test_user_id,
        question_count=1,
    )

    response = await client.post(
        f"/interview/{interview.interview_id}/answers",
        json={
            "question_id": 1,
            "answer": "FastAPI uses Depends for dependency injection.",
        },
    )

    assert response.status_code == 200

    assert await get_saved_answers(test_session, interview.interview_id) == {
        1: "FastAPI uses Depends for dependency injection.",
    }


@pytest.mark.asyncio
async def test_resubmitting_answer_replaces_it(
    client,
    test_session,
    test_user_id,
):
    interview = await create_test_interview(
        test_session,
        test_user_id,
        question_count=1,
    )

    for answer in ["First answer.", "Second answer."]:
        response = await client.post(
            f"/interview/{interview.interview_id}/answers",
            json={"question_id": 1, "answer": answer},
        )

        assert response.status_code == 200

    assert await get_saved_answers(test_session, interview.interview_id) == {
        1: "Second answer.",
    }


@pytest.mark.asyncio
async def test_answer_to_unknown_question_is_rejected(
    client,
    test_session,
    test_user_id,
):
    interview = await create_test_interview(
        test_session,
        test_user_id,
        question_count=1,
    )

    response = await client.post(
        f"/interview/{interview.interview_id}/answers",
        json={"question_id": 9, "answer": "Answer."},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Question does not belong to this interview."
    )


@pytest.mark.asyncio
async def test_submit_requires_all_answers(
    client,
    test_session,
    test_user_id,
):
    interview = await create_test_interview(test_session, test_user_id)

    await client.post(
        f"/interview/{interview.interview_id}/answers",
        json={"question_id": 1, "answer": "Only one answer."},
    )

    response = await client.post(f"/interview/{interview.interview_id}/submit")

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Please answer all questions before submitting."
    )


@pytest.mark.asyncio
async def test_submit_interview_saves_evaluations_and_result(
    client,
    test_session,
    test_user_id,
    monkeypatch,
):
    interview = await create_test_interview(test_session, test_user_id)

    for question_id in range(1, 6):
        await client.post(
            f"/interview/{interview.interview_id}/answers",
            json={
                "question_id": question_id,
                "answer": f"Answer {question_id}.",
            },
        )

    async def fake_evaluate(resume_text, job_description, questions, answers):
        assert answers == {
            question_id: f"Answer {question_id}."
            for question_id in range(1, 6)
        }

        return make_evaluations([question.id for question in questions])

    monkeypatch.setattr(
        interview_completion,
        "evaluate_interview",
        fake_evaluate,
    )

    response = await client.post(f"/interview/{interview.interview_id}/submit")

    assert response.status_code == 200

    report = response.json()

    # 8*0.40 + 7*0.25 + 6*0.20 + 9*0.15 = 7.5 -> 75
    assert report["overall_score"] == 75
    assert report["recommendation"] == "good"
    assert report["total_questions"] == 5
    assert [item["question_id"] for item in report["question_results"]] == [
        1, 2, 3, 4, 5,
    ]
    assert report["question_results"][0]["evidence"] == ["Evidence 1"]

    # This session created the attempt; reload its cached copy.
    attempt = (
        await test_session.execute(
            select(InterviewAttemptModel)
            .where(InterviewAttemptModel.interview_id == interview.interview_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()

    assert attempt.status == InterviewStatus.COMPLETED
    assert attempt.completed_at is not None

    evaluations = (
        await test_session.execute(select(AnswerEvaluationModel))
    ).scalars().all()

    assert len(evaluations) == 5
    assert {evaluation.score for evaluation in evaluations} == {75}

    # The result endpoint rebuilds the same report from the tables.
    result = await client.get(f"/interview/{interview.interview_id}/result")

    assert result.status_code == 200
    assert result.json() == report

    # Submitting again returns the saved result without calling the AI.
    async def should_not_evaluate(*args, **kwargs):
        raise AssertionError("AI should not be called again.")

    monkeypatch.setattr(
        interview_completion,
        "evaluate_interview",
        should_not_evaluate,
    )

    again = await client.post(f"/interview/{interview.interview_id}/submit")

    assert again.status_code == 200
    assert again.json() == report

    status_response = await client.get(f"/interview/{interview.interview_id}")

    assert status_response.json() == {
        "interview_id": str(interview.interview_id),
        "total_questions": 5,
        "answered_questions": 5,
        "completed": True,
    }

    late_answer = await client.post(
        f"/interview/{interview.interview_id}/answers",
        json={"question_id": 1, "answer": "Too late."},
    )

    assert late_answer.status_code == 400

    listing = (await client.get("/interview/")).json()

    assert listing[0]["status"] == "completed"
    assert listing[0]["overall_score"] == 75
    assert listing[0]["recommendation"] == "good"


@pytest.mark.asyncio
async def test_result_of_unfinished_interview_is_conflict(
    client,
    test_session,
    test_user_id,
):
    interview = await create_test_interview(test_session, test_user_id)

    response = await client.get(f"/interview/{interview.interview_id}/result")

    assert response.status_code == 409


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

    own_interview = await create_test_interview(
        test_session,
        test_user_id,
        question_count=2,
    )
    await create_test_interview(
        test_session,
        other_user.user_id,
        question_count=2,
    )

    await client.post(
        f"/interview/{own_interview.interview_id}/answers",
        json={"question_id": 1, "answer": "FastAPI uses Depends."},
    )

    response = await client.get("/interview/")

    assert response.status_code == 200

    body = response.json()

    assert len(body) == 1
    assert body[0]["interview_id"] == str(own_interview.interview_id)
    assert body[0]["status"] == "in_progress"
    assert body[0]["total_questions"] == 2
    assert body[0]["answered_questions"] == 1
    assert body[0]["overall_score"] is None
    assert body[0]["recommendation"] is None
