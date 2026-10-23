from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Enum as SQLAlchemyEnum,
    ForeignKey,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, enum_values
from app.schemas.interview import Difficulty, QuestionCategory

if TYPE_CHECKING:
    from app.models.answer import AnswerModel
    from app.models.interview_attempt import InterviewAttemptModel


class QuestionModel(CreatedAtMixin, Base):
    __tablename__ = "questions"

    # Also serves as the index for interview_attempt_id lookups.
    __table_args__ = (
        UniqueConstraint("interview_attempt_id", "position"),
    )

    question_id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )

    interview_attempt_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "interview_attempts.interview_attempt_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    # The integer question id the API and frontend use (1..5).
    position: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    question: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    category: Mapped[QuestionCategory] = mapped_column(
        SQLAlchemyEnum(
            QuestionCategory,
            native_enum=False,
            create_constraint=False,
            values_callable=enum_values,
            length=30,
        ),
        nullable=False,
    )

    difficulty: Mapped[Difficulty] = mapped_column(
        SQLAlchemyEnum(
            Difficulty,
            native_enum=False,
            create_constraint=False,
            values_callable=enum_values,
            length=10,
        ),
        nullable=False,
    )

    expected_topics: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
    )

    interview_attempt: Mapped["InterviewAttemptModel"] = relationship(
        back_populates="questions",
    )

    answer: Mapped["AnswerModel | None"] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
