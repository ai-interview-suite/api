from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.answer_evaluation import AnswerEvaluationModel
from app.models.interview_attempt import InterviewStatus
from app.models.interview_attempt_evaluation import (
    InterviewAttemptEvaluationModel,
)
from app.repositories.interview_repository import get_latest_attempt
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
    build_result_report,
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

    attempt = await get_latest_attempt(
        db=db,
        interview_id=interview_id,
        user_id=user_id,
    )

    if attempt is None:
        raise LookupError("Interview not found.")

    # Return the saved result instead of calling AI again.
    if attempt.status == InterviewStatus.COMPLETED:
        return build_result_report(attempt)

    if any(question.answer is None for question in attempt.questions):
        raise ValueError(
            "Please answer all questions before submitting."
        )

    questions = [
        InterviewQuestion(
            id=question.position,
            question=question.question,
            category=question.category,
            difficulty=question.difficulty,
            expected_topics=question.expected_topics,
        )
        for question in attempt.questions
    ]

    answers_by_id = {
        question.position: question.answer.answer
        for question in attempt.questions
    }

    evaluation = await evaluate_interview(
        resume_text=attempt.interview.resume_text,
        job_description=attempt.interview.job_description,
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

    results_by_id = {
        result.question_id: result
        for result in build_question_results(evaluation.evaluations)
    }

    for question in attempt.questions:
        result = results_by_id[question.position]

        question.answer.evaluation = AnswerEvaluationModel(
            score=result.score,
            technical_accuracy=result.technical_accuracy,
            relevance=result.relevance,
            completeness=result.completeness,
            communication=result.communication,
            feedback=result.feedback,
            evaluation={
                "evidence": result.evidence,
                "strengths": result.strengths,
                "weaknesses": result.weaknesses,
            },
        )

    attempt.evaluation = InterviewAttemptEvaluationModel(
        overall_score=overall_score,
        recommendation=recommendation,
        conclusion=build_conclusion(
            score=overall_score,
            recommendation=recommendation,
        ),
    )
    attempt.status = InterviewStatus.COMPLETED
    attempt.completed_at = datetime.now(timezone.utc)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()

        # A concurrent submit may have saved its evaluation first.
        saved_attempt = await get_latest_attempt(
            db=db,
            interview_id=interview_id,
            user_id=user_id,
        )

        if (
            saved_attempt is None
            or saved_attempt.status != InterviewStatus.COMPLETED
        ):
            raise

        return build_result_report(saved_attempt)
    except Exception:
        await db.rollback()
        raise

    return build_result_report(attempt)
