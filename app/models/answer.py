from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.answer_evaluation import AnswerEvaluationModel
    from app.models.question import QuestionModel


class AnswerModel(TimestampMixin, Base):
    __tablename__ = "answers"

    answer_id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )

    # Unique: one answer per question.
    question_id: Mapped[UUID] = mapped_column(
        ForeignKey("questions.question_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    answer: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    question: Mapped["QuestionModel"] = relationship(
        back_populates="answer",
    )

    evaluation: Mapped["AnswerEvaluationModel | None"] = relationship(
        back_populates="answer",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
