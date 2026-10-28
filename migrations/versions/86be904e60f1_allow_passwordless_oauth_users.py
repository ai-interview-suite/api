"""Allow passwordless OAuth users

Revision ID: 86be904e60f1
Revises: 6bb6c25402bc
Create Date: 2026-10-28 23:48:08.880668

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '86be904e60f1'
down_revision: Union[str, Sequence[str], None] = '6bb6c25402bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(length=255),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(length=255),
        nullable=False,
    )