from uuid import uuid4

import pytest
from app.schemas.interview import (
    Difficulty,
    InterviewQuestion,
    QuestionCategory,
)
from app.services.interview_state import (
    create_interview,
    get_interview,
    save_answer,
)


def create_test_question():

    return InterviewQuestion(
        id=1,
        question="Explain dependency injection in FastAPI.",
        category=QuestionCategory.TECHNICAL,
        difficulty=Difficulty.MEDIUM,
        expected_topics=[
            "dependency injection",
            "Depends",
        ],
    )


def test_create_interview():

    question = create_test_question()

    interview_id = create_interview(
        user_id=uuid4(),
        resume_text="Python developer with FastAPI experience.",
        job_description="Looking for a Python backend developer.",
        questions=[question],
    )

    interview = get_interview(interview_id)

    assert interview is not None
    assert len(interview.questions) == 1
    assert interview.answers == {}

def test_save_answer():

    question = create_test_question()

    interview_id = create_interview(
        user_id=uuid4(),
        resume_text="Python developer.",
        job_description="Backend developer.",
        questions=[question],
    )

    save_answer(
        interview_id=interview_id,
        question_id=1,
        answer="FastAPI uses Depends for dependency injection.",
    )

    interview = get_interview(interview_id)

    assert interview is not None

    assert interview.answers[1] == (
        "FastAPI uses Depends for dependency injection."
    )

def test_cannot_answer_unknown_question():

    question = create_test_question()

    interview_id = create_interview(
        user_id=uuid4(),
        resume_text="Python developer.",
        job_description="Backend developer.",
        questions=[question],
    )

    with pytest.raises(ValueError):
        save_answer(
            interview_id=interview_id,
            question_id=999,
            answer="Some answer.",
        )