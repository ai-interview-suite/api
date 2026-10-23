from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin

if TYPE_CHECKING:
    from app.models.answer import AnswerModel


class AnswerEvaluationModel(CreatedAtMixin, Base):
    __tablename__ = "answer_evaluations"

    answer_evaluation_id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )

    # Unique: one evaluation per answer.
    answer_id: Mapped[UUID] = mapped_column(
        ForeignKey("answers.answer_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Weighted 0-100 score from app.services.scoring.
    score: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    technical_accuracy: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    relevance: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    completeness: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    communication: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    feedback: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # {"evidence": [...], "strengths": [...], "weaknesses": [...]}
    evaluation: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    answer: Mapped["AnswerModel"] = relationship(
        back_populates="evaluation",
    )
