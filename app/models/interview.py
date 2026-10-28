from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.interview_attempt import InterviewAttemptModel


class InterviewModel(TimestampMixin, Base):
    __tablename__ = "interviews"

    interview_id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )

    # Indexed by ix_interviews_user_id_created_at below.
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"),
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
