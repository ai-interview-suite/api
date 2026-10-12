from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.interview import (
    InterviewAnswerModel,
    InterviewModel,
    InterviewStatus,
)
from app.schemas.interview import InterviewQuestion


async def create_interview(
    db: AsyncSession,
    user_id: UUID,
    resume_text: str,
    job_description: str,
    questions: list[InterviewQuestion],
) -> InterviewModel:

    question_data = [
        question.model_dump(mode="json")
        for question in questions
    ]

    interview = InterviewModel(
        user_id=user_id,
        resume_text=resume_text,
        job_description=job_description,
        questions=question_data,
        status=InterviewStatus.IN_PROGRESS,
    )

    db.add(interview)
    await db.commit()
    await db.refresh(interview)

    return interview


async def get_user_interview(
    db: AsyncSession,
    interview_id: UUID,
    user_id: UUID,
) -> InterviewModel | None:

    result = await db.execute(
        select(InterviewModel)
        .where(
            InterviewModel.id == interview_id,
            InterviewModel.user_id == user_id,
        )
        .options(
            selectinload(InterviewModel.answers)
        )
    )

    return result.scalar_one_or_none()


async def save_interview_answer(
    db: AsyncSession,
    interview: InterviewModel,
    question_id: int,
    answer: str,
) -> InterviewAnswerModel:

    if interview.status != InterviewStatus.IN_PROGRESS:
        raise ValueError(
            "This interview is already completed."
        )
    
    if not question_belongs_to_interview(
        interview,
        question_id,
    ):
        raise ValueError(
            "Question does not belong to this interview."
        )

    existing_answer =   next(
        (
            item
            for item in interview.answers
            if item.question_id == question_id
        ),
        None,
    )

    if existing_answer is not None:
        existing_answer.answer = answer
        await db.commit()
        await db.refresh(existing_answer)
        return existing_answer

    saved_answer = InterviewAnswerModel(
        interview_id=interview.id,
        question_id=question_id,
        answer=answer,
    )

    db.add(saved_answer)
    await db.commit()
    await db.refresh(saved_answer)

    return saved_answer

def question_belongs_to_interview(
    interview: InterviewModel,
    question_id: int,
) -> bool:

    return any(
        question["id"] == question_id
        for question in interview.questions
    )