from app.schemas.interview import AnswerEvaluation
from app.services.scoring import (
    build_question_results,
    calculate_answer_score,
    calculate_overall_score,
)


def test_perfect_answer_gets_100():

    evaluation = AnswerEvaluation(
        question_id=1,
        technical_accuracy=10,
        relevance=10,
        completeness=10,
        communication=10,
        evidence=["Explained the request lifecycle in detail."],
        strengths=["Excellent technical explanation."],
        weaknesses=["No major weaknesses."],
        feedback="Excellent answer.",
    )

    score = calculate_answer_score(evaluation)

    assert score == 100

def test_weak_answer_gets_low_score():

    evaluation = AnswerEvaluation(
        question_id=1,
        technical_accuracy=2,
        relevance=3,
        completeness=2,
        communication=4,
        evidence=["Mentioned the topic without explaining it."],
        strengths=["Attempted to answer the question."],
        weaknesses=["Missing important technical details."],
        feedback="The answer needs improvement.",
    )

    score = calculate_answer_score(evaluation)

    assert score == 26

def test_overall_score_is_average():

    evaluations = [
        AnswerEvaluation(
            question_id=1,
            technical_accuracy=10,
            relevance=10,
            completeness=10,
            communication=10,
            evidence=["Gave a concrete implementation example."],
            strengths=["Excellent."],
            weaknesses=["None."],
            feedback="Excellent answer.",
        ),
        AnswerEvaluation(
            question_id=2,
            technical_accuracy=6,
            relevance=6,
            completeness=6,
            communication=6,
            evidence=["Named the relevant concepts."],
            strengths=["Good."],
            weaknesses=["Needs more detail."],
            feedback="Good answer.",
        ),
    ]

    score = calculate_overall_score(
        evaluations
    )

    assert score == 80

def test_build_question_results_carries_evaluation_details():

    evaluation = AnswerEvaluation(
        question_id=3,
        technical_accuracy=8,
        relevance=7,
        completeness=6,
        communication=9,
        evidence=["Walked through the caching layer."],
        strengths=["Clear explanation."],
        weaknesses=["Did not mention tradeoffs."],
        feedback="A solid answer overall.",
    )

    results = build_question_results([evaluation])

    assert len(results) == 1

    result = results[0]

    assert result.question_id == 3
    assert result.score == calculate_answer_score(evaluation)
    assert result.evidence == evaluation.evidence
    assert result.strengths == evaluation.strengths
    assert result.weaknesses == evaluation.weaknesses
    assert result.feedback == evaluation.feedback
