from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Enum as SQLAlchemyEnum,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, enum_values
from app.schemas.interview import InterviewRecommendation

if TYPE_CHECKING:
    from app.models.interview_attempt import InterviewAttemptModel


class InterviewAttemptEvaluationModel(CreatedAtMixin, Base):
    __tablename__ = "interview_attempt_evaluations"

    interview_attempt_evaluation_id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )

    # Unique: one evaluation per attempt.
    interview_attempt_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "interview_attempts.interview_attempt_id",
            ondelete="CASCADE",
        ),
        unique=True,
        nullable=False,
    )

    overall_score: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    recommendation: Mapped[InterviewRecommendation] = mapped_column(
        SQLAlchemyEnum(
            InterviewRecommendation,
            native_enum=False,
            create_constraint=False,
            values_callable=enum_values,
            length=30,
        ),
        nullable=False,
    )

    conclusion: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    interview_attempt: Mapped["InterviewAttemptModel"] = relationship(
        back_populates="evaluation",
    )
