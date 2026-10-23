from uuid import UUID

from sqlalchemy import Row, func, select
from sqlalchemy.dialects.postgresql import distinct_on, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, selectinload

from app.models.answer import AnswerModel
from app.models.interview import InterviewModel
from app.models.interview_attempt import (
    InterviewAttemptModel,
    InterviewStatus,
)
from app.models.interview_attempt_evaluation import (
    InterviewAttemptEvaluationModel,
)
from app.models.question import QuestionModel
from app.schemas.interview import InterviewQuestion


async def create_interview(
    db: AsyncSession,
    user_id: UUID,
    resume_text: str,
    job_description: str,
    questions: list[InterviewQuestion],
) -> InterviewModel:

    attempt = InterviewAttemptModel(
        attempt_number=1,
        status=InterviewStatus.IN_PROGRESS,
        questions=[
            QuestionModel(
                position=question.id,
                question=question.question,
                category=question.category,
                difficulty=question.difficulty,
                expected_topics=question.expected_topics,
            )
            for question in questions
        ],
    )

    interview = InterviewModel(
        user_id=user_id,
        resume_text=resume_text,
        job_description=job_description,
        attempts=[attempt],
    )

    db.add(interview)
    await db.commit()

    return interview


async def get_latest_attempt(
    db: AsyncSession,
    interview_id: UUID,
    user_id: UUID,
) -> InterviewAttemptModel | None:
    """Latest attempt of the user's interview, with everything needed
    to show, answer or evaluate it."""

    result = await db.execute(
        select(InterviewAttemptModel)
        .join(InterviewAttemptModel.interview)
        .where(
            InterviewModel.interview_id == interview_id,
            InterviewModel.user_id == user_id,
        )
        .order_by(InterviewAttemptModel.attempt_number.desc())
        .limit(1)
        .options(
            contains_eager(InterviewAttemptModel.interview),
            selectinload(InterviewAttemptModel.questions)
            .selectinload(QuestionModel.answer)
            .selectinload(AnswerModel.evaluation),
            selectinload(InterviewAttemptModel.evaluation),
        )
    )

    return result.scalar_one_or_none()


async def get_user_interview_summaries(
    db: AsyncSession,
    user_id: UUID,
) -> list[Row]:
    """One row per interview, newest first, describing its latest
    attempt. Counts are done in SQL, so no answers or resumes load."""

    latest_attempt = (
        select(InterviewAttemptModel)
        .ext(distinct_on(InterviewAttemptModel.interview_id))
        .order_by(
            InterviewAttemptModel.interview_id,
            InterviewAttemptModel.attempt_number.desc(),
        )
        .subquery()
    )

    total_questions = (
        select(func.count())
        .where(
            QuestionModel.interview_attempt_id
            == latest_attempt.c.interview_attempt_id
        )
        .scalar_subquery()
    )

    answered_questions = (
        select(func.count())
        .select_from(AnswerModel)
        .join(AnswerModel.question)
        .where(
            QuestionModel.interview_attempt_id
            == latest_attempt.c.interview_attempt_id
        )
        .scalar_subquery()
    )

    result = await db.execute(
        select(
            InterviewModel.interview_id,
            InterviewModel.job_description,
            InterviewModel.created_at,
            latest_attempt.c.status,
            total_questions.label("total_questions"),
            answered_questions.label("answered_questions"),
            InterviewAttemptEvaluationModel.overall_score,
            InterviewAttemptEvaluationModel.recommendation,
        )
        .join(
            latest_attempt,
            latest_attempt.c.interview_id == InterviewModel.interview_id,
        )
        .outerjoin(
            InterviewAttemptEvaluationModel,
            InterviewAttemptEvaluationModel.interview_attempt_id
            == latest_attempt.c.interview_attempt_id,
        )
        .where(InterviewModel.user_id == user_id)
        .order_by(InterviewModel.created_at.desc())
    )

    return list(result.all())


async def save_answer(
    db: AsyncSession,
    attempt: InterviewAttemptModel,
    question_id: int,
    answer: str,
) -> None:
    """Save or replace the answer to the question at position
    question_id (the id the API uses)."""

    if attempt.status != InterviewStatus.IN_PROGRESS:
        raise ValueError(
            "This interview is already completed."
        )

    question = next(
        (
            item
            for item in attempt.questions
            if item.position == question_id
        ),
        None,
    )

    if question is None:
        raise ValueError(
            "Question does not belong to this interview."
        )

    # Upsert, so two quick submits of the same answer can't collide
    # on the one-answer-per-question unique constraint.
    statement = insert(AnswerModel).values(
        question_id=question.question_id,
        answer=answer,
    )

    await db.execute(
        statement.on_conflict_do_update(
            index_elements=[AnswerModel.question_id],
            set_={
                "answer": statement.excluded.answer,
                "updated_at": func.now(),
            },
        )
    )
    await db.commit()

