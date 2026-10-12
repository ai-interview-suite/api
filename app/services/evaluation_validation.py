from app.schemas.interview import (
    AnswerEvaluation,
    InterviewQuestion,
)


def validate_evaluation_question_ids(
    questions: list[InterviewQuestion],
    evaluations: list[AnswerEvaluation],
) -> None:
    expected_ids = {
        question.id
        for question in questions
    }

    actual_ids = [
        evaluation.question_id
        for evaluation in evaluations
    ]

    if len(actual_ids) != len(set(actual_ids)):
        raise ValueError(
            "AI returned duplicate question evaluations."
        )

    if set(actual_ids) != expected_ids:
        raise ValueError(
            "AI did not evaluate the expected questions."
        )