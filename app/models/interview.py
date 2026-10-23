from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Enum as SQLAlchemyEnum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
# Old interviews.status column; moves to interview_attempts.
from app.models.interview_attempt import InterviewStatus

if TYPE_CHECKING:
    from app.models.interview_attempt import InterviewAttemptModel


class InterviewModel(TimestampMixin, Base):
    __tablename__ = "interviews"

    # Renamed to interview_id together with the code switch, so the
    # code running during the migration keeps working.
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
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

    # Old columns, replaced by interview_attempts and questions.
    # Nullable so new code can stop writing them before they are dropped.
    questions: Mapped[list[dict] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    status: Mapped[InterviewStatus | None] = mapped_column(
        SQLAlchemyEnum(InterviewStatus),
        default=InterviewStatus.IN_PROGRESS,
        nullable=True,
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

    answers: Mapped[list["InterviewAnswerModel"]] = relationship(
        back_populates="interview",
        cascade="all, delete-orphan",
    )

    evaluation_summary: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    attempts: Mapped[list["InterviewAttemptModel"]] = relationship(
        back_populates="interview",
        order_by="InterviewAttemptModel.attempt_number",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


# Serves "my interviews, newest first".
Index(
    "ix_interviews_user_id_created_at",
    InterviewModel.user_id,
    InterviewModel.created_at.desc(),
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