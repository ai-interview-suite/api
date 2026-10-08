from app.schemas.interview import AnswerEvaluation, InterviewQuestionResult


def calculate_answer_score(
    evaluation: AnswerEvaluation,
) -> int:

    score = (
        evaluation.technical_accuracy * 0.40
        + evaluation.relevance * 0.25
        + evaluation.completeness * 0.20
        + evaluation.communication * 0.15
    )

    return round(score * 10)


def calculate_overall_score(
    evaluations: list[AnswerEvaluation],
) -> int:

    if not evaluations:
        return 0

    scores = [
        calculate_answer_score(evaluation)
        for evaluation in evaluations
    ]

    return round(sum(scores) / len(scores))

def build_question_results(
    evaluations: list[AnswerEvaluation],
) -> list[InterviewQuestionResult]:

    results = []

    for evaluation in evaluations:
        score = calculate_answer_score(evaluation)

        results.append(
            InterviewQuestionResult(
                question_id=evaluation.question_id,
                score=score,
                technical_accuracy=(
                    evaluation.technical_accuracy
                ),
                relevance=evaluation.relevance,
                completeness=evaluation.completeness,
                communication=evaluation.communication,
                evidence=evaluation.evidence,
                strengths=evaluation.strengths,
                weaknesses=evaluation.weaknesses,
                feedback=evaluation.feedback,
            )
        )

    return results