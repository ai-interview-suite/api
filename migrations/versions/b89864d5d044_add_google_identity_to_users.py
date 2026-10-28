"""Add Google identity to users

Revision ID: b89864d5d044
Revises: 86be904e60f1
Create Date: 2026-10-29 00:05:06.106213

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b89864d5d044'
down_revision: Union[str, Sequence[str], None] = '86be904e60f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("google_sub", sa.String(length=255), nullable=True),
    )
    op.create_unique_constraint(
        "uq_users_google_sub",
        "users",
        ["google_sub"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_users_google_sub",
        "users",
        type_="unique",
    )
    op.drop_column("users", "google_sub")