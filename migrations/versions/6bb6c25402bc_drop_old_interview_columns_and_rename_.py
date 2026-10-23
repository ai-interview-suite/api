"""drop old interview columns and rename primary keys

Contract step: the old interview columns and interview_answers are no
longer read or written. First copies any interview the old code created
after 943dab65b4f8 ran, then drops the old structure and renames
users.id / interviews.id to user_id / interview_id.

The renames need the matching code: deploy it right after this runs.

Downgrade rebuilds the old structure empty; downgrading further to
2753a0b77454 refills it from the new tables.

Revision ID: 6bb6c25402bc
Revises: 943dab65b4f8
Create Date: 2026-10-23 09:29:04.375881

"""
import importlib.util
from pathlib import Path
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6bb6c25402bc'
down_revision: Union[str, Sequence[str], None] = '943dab65b4f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def load_copy_revision():
    # Reuse the copy and checks of 943dab65b4f8 instead of repeating them.
    path = Path(__file__).with_name(
        '943dab65b4f8_copy_interviews_into_attempts_questions_.py'
    )
    spec = importlib.util.spec_from_file_location('copy_revision', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def upgrade() -> None:
    """Upgrade schema."""

    copy_revision = load_copy_revision()
    bind = op.get_bind()

    # Still there when 943dab65b4f8 ran in this same transaction.
    bind.execute(sa.text('DROP TABLE IF EXISTS copied_attempts'))

    for statement in copy_revision.COPY_STATEMENTS:
        bind.execute(sa.text(statement))

    failures = {
        name: count
        for name, query in copy_revision.CHECKS.items()
        if (count := bind.execute(sa.text(query)).scalar_one())
    }

    if failures:
        raise RuntimeError(f'Interview copy is incomplete: {failures}')

    # --- drop the old structure --------------------------------------

    op.drop_table('interview_answers')

    op.drop_column('interviews', 'questions')
    op.drop_column('interviews', 'status')
    op.drop_column('interviews', 'overall_score')
    op.drop_column('interviews', 'recommendation')
    op.drop_column('interviews', 'conclusion')
    op.drop_column('interviews', 'evaluation_summary')
    sa.Enum(name='interviewstatus').drop(bind, checkfirst=True)

    # Covered by ix_interviews_user_id_created_at.
    op.drop_index('ix_interviews_user_id', table_name='interviews')

    # --- rename primary keys (foreign keys follow automatically) -----

    op.alter_column('users', 'id', new_column_name='user_id')
    op.alter_column('interviews', 'id', new_column_name='interview_id')


def downgrade() -> None:
    """Downgrade schema."""

    op.alter_column('interviews', 'interview_id', new_column_name='id')
    op.alter_column('users', 'user_id', new_column_name='id')

    op.create_index('ix_interviews_user_id', 'interviews', ['user_id'])

    status_type = sa.Enum('IN_PROGRESS', 'COMPLETED', name='interviewstatus')
    status_type.create(op.get_bind())

    # Same shape as at 943dab65b4f8: nullable, filled by its downgrade.
    op.add_column('interviews', sa.Column('questions', sa.JSON(), nullable=True))
    op.add_column('interviews', sa.Column('status', status_type, nullable=True))
    op.add_column('interviews', sa.Column('overall_score', sa.Integer(), nullable=True))
    op.add_column('interviews', sa.Column('recommendation', sa.String(length=50), nullable=True))
    op.add_column('interviews', sa.Column('conclusion', sa.Text(), nullable=True))
    op.add_column('interviews', sa.Column('evaluation_summary', sa.JSON(), nullable=True))

    op.create_table(
        'interview_answers',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('interview_id', sa.Uuid(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('evaluation', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['interview_id'], ['interviews.id'], name='fk_interview_answers_interview_id_interviews', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_interview_answers'),
        sa.UniqueConstraint('interview_id', 'question_id', name='uq_interview_answer_question'),
    )
    op.create_index('ix_interview_answers_interview_id', 'interview_answers', ['interview_id'])
