from app.schemas.interview import AnswerEvaluation
from app.services.scoring import (
    calculate_answer_score,
    calculate_overall_score,
)


def make_evaluation(
    question_id: int,
    score: int,
) -> AnswerEvaluation:
    return AnswerEvaluation(
        question_id=question_id,
        technical_accuracy=score,
        relevance=score,
        completeness=score,
        communication=score,
        evidence=["The answer explains the key concept."],
        strengths=["Explains the concept clearly."],
        weaknesses=["Could provide more detail."],
        feedback="The answer demonstrates this level of understanding.",
    )


def test_perfect_answer_scores_100():
    evaluation = make_evaluation(1, 10)

    assert calculate_answer_score(evaluation) == 100


def test_zero_score_answer_scores_zero():
    evaluation = make_evaluation(1, 0)

    assert calculate_answer_score(evaluation) == 0


def test_overall_score_is_average():
    evaluations = [
        make_evaluation(1, 10),
        make_evaluation(2, 6),
    ]

    assert calculate_overall_score(evaluations) == 80


def test_empty_evaluations_return_zero():
    assert calculate_overall_score([]) == 0