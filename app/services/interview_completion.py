from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview import InterviewStatus
from app.repositories.interview_repository import get_user_interview
from app.schemas.interview import (
    InterviewQuestion,
    InterviewResultResponse,
)
from app.services.ai_service import evaluate_interview
from app.services.evaluation_validation import (
    validate_evaluation_question_ids,
)
from app.services.result_service import (
    build_conclusion,
    get_recommendation,
)
from app.services.scoring import (
    build_question_results,
    calculate_overall_score,
)


async def complete_interview(
    db: AsyncSession,
    interview_id: UUID,
    user_id: UUID,
) -> InterviewResultResponse:

    interview = await get_user_interview(
        db=db,
        interview_id=interview_id,
        user_id=user_id,
    )

    if interview is None:
        raise LookupError("Interview not found.")

    # Return the saved result instead of calling AI again.
    if interview.status == InterviewStatus.COMPLETED:
        if interview.evaluation_summary is None:
            raise RuntimeError(
                "Completed interview has no saved evaluation."
            )

        return InterviewResultResponse.model_validate(
            interview.evaluation_summary
        )

    question_ids = {
        question["id"]
        for question in interview.questions
    }

    answers_by_id = {
        answer.question_id: answer.answer
        for answer in interview.answers
    }

    if set(answers_by_id) != question_ids:
        raise ValueError(
            "Please answer all questions before submitting."
        )

    questions = [
        InterviewQuestion.model_validate(item)
        for item in interview.questions
    ]

    evaluation = await evaluate_interview(
        resume_text=interview.resume_text,
        job_description=interview.job_description,
        questions=questions,
        answers=answers_by_id,
    )

    validate_evaluation_question_ids(
        questions=questions,
        evaluations=evaluation.evaluations,
    )

    overall_score = calculate_overall_score(
        evaluation.evaluations
    )

    recommendation = get_recommendation(
        overall_score
    )

    conclusion = build_conclusion(
        score=overall_score,
        recommendation=recommendation,
    )

    question_results = build_question_results(
        evaluation.evaluations
    )

    report = InterviewResultResponse(
        interview_id=interview.id,
        overall_score=overall_score,
        recommendation=recommendation,
        conclusion=conclusion,
        total_questions=len(questions),
        question_results=question_results,
    )

    evaluations_by_id = {
        item.question_id: item
        for item in evaluation.evaluations
    }

    for answer in interview.answers:
        item = evaluations_by_id[answer.question_id]

        answer.score = next(
            result.score
            for result in question_results
            if result.question_id == answer.question_id
        )

        answer.evaluation = item.model_dump(mode="json")

    interview.overall_score = overall_score
    interview.recommendation = recommendation.value
    interview.conclusion = conclusion
    interview.evaluation_summary = report.model_dump(
        mode="json"
    )
    interview.status = InterviewStatus.COMPLETED

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return report