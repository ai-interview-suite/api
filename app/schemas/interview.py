from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
from uuid import UUID

class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class QuestionCategory(str, Enum):
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    EXPERIENCE = "experience"
    PROBLEM_SOLVING = "problem_solving"
    SYSTEM_DESIGN = "system_design"

class InterviewRecommendation(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    BORDERLINE = "borderline"
    NEEDS_IMPROVEMENT = "needs_improvement"

class InterviewQuestion(BaseModel):
    id: int = Field(ge=1)
    question: str = Field(min_length=10)
    category: QuestionCategory
    difficulty: Difficulty
    expected_topics: list[str] = Field(min_length=1)

class InterviewQuestionsResponse(BaseModel):
    questions: list[InterviewQuestion] = Field(
        min_length=5,
        max_length=5
    )

class InterviewStartResponse(BaseModel):
    interview_id: UUID
    questions: list[InterviewQuestion]

class InterviewSummary(BaseModel):
    interview_id: UUID
    job_description: str
    status: str
    total_questions: int
    answered_questions: int
    overall_score: int | None
    recommendation: str | None
    created_at: datetime

class InterviewAnswerRequest(BaseModel):
    question_id: int = Field(ge=1)
    answer: str = Field(min_length=1, max_length=5000)


# Evaluation Models
class AnswerEvaluation(BaseModel):
    question_id: int = Field(ge=1)

    technical_accuracy: int = Field(
        ge=0,
        le=10,
    )

    relevance: int = Field(
        ge=0,
        le=10,
    )

    completeness: int = Field(
        ge=0,
        le=10,
    )

    communication: int = Field(
        ge=0,
        le=10,
    )

    evidence: list[str] = Field(
        min_length=1,
    )

    strengths: list[str] = Field(
        min_length=1,
    )

    weaknesses: list[str] = Field(
        min_length=1,
    )

    feedback: str = Field(
        min_length=10,
    )

    

class InterviewEvaluationResponse(BaseModel):
    evaluations: list[AnswerEvaluation] = Field(
        min_length=5,
        max_length=5
    )

class InterviewQuestionResult(BaseModel):
    question_id: int = Field(ge=1)
    score: int = Field(ge=0, le=100)

    technical_accuracy: int = Field(
        ge=0,
        le=10,
    )

    relevance: int = Field(
        ge=0,
        le=10,
    )

    completeness: int = Field(
        ge=0,
        le=10,
    )

    communication: int = Field(
        ge=0,
        le=10,
    )

    evidence: list[str] = Field(
        min_length=1,
    )

    strengths: list[str] = Field(
        min_length=1,
    )

    weaknesses: list[str] = Field(
        min_length=1,
    )

    feedback: str = Field(
        min_length=10,
    )


class InterviewResultResponse(BaseModel):
    interview_id: UUID

    overall_score: int = Field(
        ge=0,
        le=100,
    )

    recommendation: InterviewRecommendation

    conclusion: str = Field(
        min_length=20,
    )

    total_questions: int = Field(
        ge=1,
    )

    question_results: list[InterviewQuestionResult]
