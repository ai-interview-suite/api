from app.schemas.interview import InterviewRecommendation


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