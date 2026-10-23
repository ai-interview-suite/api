from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    SmallInteger,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, enum_values

if TYPE_CHECKING:
    from app.models.interview import InterviewModel
    from app.models.interview_attempt_evaluation import (
        InterviewAttemptEvaluationModel,
    )
    from app.models.question import QuestionModel


class InterviewStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class InterviewAttemptModel(TimestampMixin, Base):
    __tablename__ = "interview_attempts"

    __table_args__ = (
        UniqueConstraint("interview_id", "attempt_number"),
    )

    interview_attempt_id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )

    interview_id: Mapped[UUID] = mapped_column(
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
    )

    attempt_number: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    status: Mapped[InterviewStatus] = mapped_column(
        SQLAlchemyEnum(
            InterviewStatus,
            native_enum=False,
            create_constraint=False,
            values_callable=enum_values,
            length=20,
        ),
        default=InterviewStatus.IN_PROGRESS,
        server_default=InterviewStatus.IN_PROGRESS.value,
        nullable=False,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    interview: Mapped["InterviewModel"] = relationship(
        back_populates="attempts",
    )

    questions: Mapped[list["QuestionModel"]] = relationship(
        back_populates="interview_attempt",
        order_by="QuestionModel.position",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    evaluation: Mapped["InterviewAttemptEvaluationModel | None"] = (
        relationship(
            back_populates="interview_attempt",
            cascade="all, delete-orphan",
            passive_deletes=True,
        )
    )
