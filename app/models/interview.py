from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class InterviewStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class InterviewModel(Base):
    __tablename__ = "interviews"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    resume_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    job_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    questions: Mapped[list[dict]] = mapped_column(
        JSON,
        nullable=False,
    )

    status: Mapped[InterviewStatus] = mapped_column(
        SQLAlchemyEnum(InterviewStatus),
        default=InterviewStatus.IN_PROGRESS,
        nullable=False,
    )

    overall_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    recommendation: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    conclusion: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    answers: Mapped[list["InterviewAnswerModel"]] = relationship(
        back_populates="interview",
        cascade="all, delete-orphan",
    )

    evaluation_summary: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

class InterviewAnswerModel(Base):
    __tablename__ = "interview_answers"

    __table_args__ = (
        UniqueConstraint(
            "interview_id",
            "question_id",
            name="uq_interview_answer_question",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    interview_id: Mapped[UUID] = mapped_column(
        ForeignKey("interviews.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    question_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    answer: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    evaluation: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    interview: Mapped["InterviewModel"] = relationship(
        back_populates="answers",
    )