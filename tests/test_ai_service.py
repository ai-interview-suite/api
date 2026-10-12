from types import SimpleNamespace

import pytest

from app.schemas.interview import (
    Difficulty,
    InterviewQuestion,
    QuestionCategory,
)
from app.services import ai_service
from app.services.exceptions import AIServiceUnavailableError


async def test_evaluate_interview_sends_answers_to_ai(monkeypatch):
    captured = {}

    async def fake_create(**kwargs):
        captured.update(kwargs)
        raise RuntimeError("Stop before parsing the response.")

    monkeypatch.setattr(
        ai_service,
        "client",
        SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=fake_create)
            )
        ),
    )

    questions = [
        InterviewQuestion(
            id=1,
            question="Explain dependency injection in FastAPI.",
            category=QuestionCategory.TECHNICAL,
            difficulty=Difficulty.MEDIUM,
            expected_topics=["Depends"],
        ),
    ]

    with pytest.raises(AIServiceUnavailableError):
        await ai_service.evaluate_interview(
            resume_text="Python developer.",
            job_description="Python backend developer.",
            questions=questions,
            answers={1: "FastAPI uses Depends for dependency injection."},
        )

    user_prompt = captured["messages"][-1]["content"]

    assert "FastAPI uses Depends for dependency injection." in user_prompt
