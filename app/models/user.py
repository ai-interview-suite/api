from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Enum as SQLAlchemyEnum, String, text
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, enum_values


class UserStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class UserModel(TimestampMixin, Base):
    __tablename__ = "users"

    # Renamed to user_id together with the code switch, so the code
    # running during the migration keeps working.
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )

    # citext makes the unique index case-insensitive.
    email: Mapped[str] = mapped_column(
        CITEXT,
        unique=True,
        index=True,
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[UserStatus] = mapped_column(
        SQLAlchemyEnum(
            UserStatus,
            native_enum=False,
            create_constraint=False,
            values_callable=enum_values,
            length=20,
        ),
        default=UserStatus.ACTIVE,
        server_default=UserStatus.ACTIVE.value,
        nullable=False,
    )
