from app.models.interview_attempt import InterviewAttemptModel
from app.schemas.interview import (
    InterviewQuestionResult,
    InterviewRecommendation,
    InterviewResultResponse,
)


def get_recommendation(
    score: int,
) -> InterviewRecommendation:

    if score >= 85:
        return InterviewRecommendation.EXCELLENT

    if score >= 70:
        return InterviewRecommendation.GOOD

    if score >= 50:
        return InterviewRecommendation.BORDERLINE

    return InterviewRecommendation.NEEDS_IMPROVEMENT


def build_conclusion(
    score: int,
    recommendation: InterviewRecommendation,
) -> str:

    if recommendation == InterviewRecommendation.EXCELLENT:
        return (
            f"The candidate demonstrated strong interview "
            f"performance with an overall score of {score}/100. "
            "Their answers showed strong technical understanding, "
            "relevance, and communication."
        )

    if recommendation == InterviewRecommendation.GOOD:
        return (
            f"The candidate demonstrated good interview "
            f"performance with an overall score of {score}/100. "
            "Most answers showed a solid understanding of the "
            "topics, with some areas that could be improved."
        )

    if recommendation == InterviewRecommendation.BORDERLINE:
        return (
            f"The candidate demonstrated mixed interview "
            f"performance with an overall score of {score}/100. "
            "Some answers were satisfactory, but several areas "
            "require further improvement."
        )

    return (
        f"The candidate's overall score was {score}/100. "
        "The interview indicates that significant improvement "
        "is needed in one or more important areas."
    )


def build_result_report(
    attempt: InterviewAttemptModel,
) -> InterviewResultResponse:
    """Rebuild the result of a completed attempt from its saved
    evaluations. Needs questions, answers and evaluations loaded."""

    if attempt.evaluation is None:
        raise RuntimeError(
            "Completed interview has no saved evaluation."
        )

    question_results = []

    for question in attempt.questions:
        evaluation = question.answer.evaluation

        question_results.append(
            InterviewQuestionResult(
                question_id=question.position,
                score=evaluation.score,
                technical_accuracy=evaluation.technical_accuracy,
                relevance=evaluation.relevance,
                completeness=evaluation.completeness,
                communication=evaluation.communication,
                evidence=evaluation.evaluation["evidence"],
                strengths=evaluation.evaluation["strengths"],
                weaknesses=evaluation.evaluation["weaknesses"],
                feedback=evaluation.feedback,
            )
        )

    return InterviewResultResponse(
        interview_id=attempt.interview_id,
        overall_score=attempt.evaluation.overall_score,
        recommendation=attempt.evaluation.recommendation,
        conclusion=attempt.evaluation.conclusion,
        total_questions=len(attempt.questions),
        question_results=question_results,
    )
