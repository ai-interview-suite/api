"""The database itself enforces relationships, not only the app."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.answer import AnswerModel
from app.models.interview_attempt import InterviewAttemptModel
from app.models.interview_attempt_evaluation import (
    InterviewAttemptEvaluationModel,
)
from app.models.user import UserModel
from app.repositories.interview_repository import create_interview
from app.schemas.interview import InterviewRecommendation
from tests.test_interview_api import make_five_questions


async def make_attempt(session, user_id) -> InterviewAttemptModel:
    interview = await create_interview(
        db=session,
        user_id=user_id,
        resume_text="Resume.",
        job_description="Job.",
        questions=make_five_questions().questions,
    )

    return interview.attempts[0]


async def assert_rejected(session, *rows) -> None:
    session.add_all(rows)

    with pytest.raises(IntegrityError):
        await session.commit()

    await session.rollback()


@pytest.mark.asyncio
async def test_answer_needs_an_existing_question(test_session, test_db):
    await assert_rejected(
        test_session,
        AnswerModel(question_id=uuid4(), answer="Orphan."),
    )


@pytest.mark.asyncio
async def test_one_answer_per_question(test_session, test_user_id):
    attempt = await make_attempt(test_session, test_user_id)
    question_id = attempt.questions[0].question_id

    test_session.add(AnswerModel(question_id=question_id, answer="First."))
    await test_session.commit()

    await assert_rejected(
        test_session,
        AnswerModel(question_id=question_id, answer="Second."),
    )


@pytest.mark.asyncio
async def test_attempt_numbers_are_unique_per_interview(
    test_session,
    test_user_id,
):
    attempt = await make_attempt(test_session, test_user_id)

    await assert_rejected(
        test_session,
        InterviewAttemptModel(
            interview_id=attempt.interview_id,
            attempt_number=1,
        ),
    )


@pytest.mark.asyncio
async def test_one_evaluation_per_attempt(test_session, test_user_id):
    attempt = await make_attempt(test_session, test_user_id)

    def evaluation():
        return InterviewAttemptEvaluationModel(
            interview_attempt_id=attempt.interview_attempt_id,
            overall_score=70,
            recommendation=InterviewRecommendation.GOOD,
            conclusion="Conclusion.",
        )

    test_session.add(evaluation())
    await test_session.commit()

    await assert_rejected(test_session, evaluation())


@pytest.mark.asyncio
async def test_email_is_unique_ignoring_case(test_session, test_db):
    test_session.add(UserModel(email="same@example.com", password_hash="h"))
    await test_session.commit()

    await assert_rejected(
        test_session,
        UserModel(email="SAME@example.com", password_hash="h"),
    )
