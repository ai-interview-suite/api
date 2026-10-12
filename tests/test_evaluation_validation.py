import pytest

from app.schemas.interview import (
    AnswerEvaluation,
    Difficulty,
    InterviewQuestion,
    QuestionCategory,
)
from app.services.evaluation_validation import (
    validate_evaluation_question_ids,
)


def make_question(question_id: int) -> InterviewQuestion:
    return InterviewQuestion(
        id=question_id,
        question=f"Explain concept number {question_id} clearly.",
        category=QuestionCategory.TECHNICAL,
        difficulty=Difficulty.MEDIUM,
        expected_topics=["explanation", "example"],
    )


def make_evaluation(question_id: int) -> AnswerEvaluation:
    return AnswerEvaluation(
        question_id=question_id,
        technical_accuracy=8,
        relevance=8,
        completeness=7,
        communication=8,
        evidence=["The candidate explained the main concept."],
        strengths=["Clear explanation."],
        weaknesses=["Some details are missing."],
        feedback="A good answer that could use more detail.",
    )


def test_accepts_matching_question_ids():
    questions = [make_question(1), make_question(2)]
    evaluations = [make_evaluation(1), make_evaluation(2)]

    validate_evaluation_question_ids(
        questions,
        evaluations,
    )


def test_rejects_duplicate_evaluation_ids():
    questions = [make_question(1), make_question(2)]
    evaluations = [make_evaluation(1), make_evaluation(1)]

    with pytest.raises(ValueError):
        validate_evaluation_question_ids(
            questions,
            evaluations,
        )


def test_rejects_missing_evaluation():
    questions = [make_question(1), make_question(2)]
    evaluations = [make_evaluation(1)]

    with pytest.raises(ValueError):
        validate_evaluation_question_ids(
            questions,
            evaluations,
        )