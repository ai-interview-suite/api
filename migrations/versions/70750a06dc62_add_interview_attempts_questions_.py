"""add interview attempts, questions, answers and evaluations

Expand step: only adds tables, columns and defaults, so existing data is
kept and the code already running keeps working while this is applied.
Old interview columns and interview_answers are copied by the next
revision; they are dropped, and users.id / interviews.id renamed to
user_id / interview_id, in a later contract revision.

Revision ID: 70750a06dc62
Revises: 2753a0b77454
Create Date: 2026-10-22 22:17:30.186448

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '70750a06dc62'
down_revision: Union[str, Sequence[str], None] = '2753a0b77454'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def rename_constraint_if_exists(table: str, old: str, new: str) -> None:
    # Databases created before the naming convention have PostgreSQL's
    # default names (users_pkey); newer ones already have the new name.
    op.execute(f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = '{old}'
                  AND conrelid = '{table}'::regclass
            ) THEN
                ALTER TABLE {table} RENAME CONSTRAINT {old} TO {new};
            END IF;
        END $$;
    """)


def upgrade() -> None:
    """Upgrade schema."""

    # --- users -------------------------------------------------------

    rename_constraint_if_exists('users', 'users_pkey', 'pk_users')
    op.alter_column(
        'users', 'id',
        server_default=sa.text('gen_random_uuid()'),
    )

    # citext would make case-only duplicates collide on the unique index.
    duplicates = op.get_bind().execute(sa.text(
        'SELECT lower(email) FROM users '
        'GROUP BY lower(email) HAVING count(*) > 1'
    )).scalars().all()

    if duplicates:
        raise RuntimeError(
            'Emails differing only by case must be merged before this '
            f'migration: {duplicates}'
        )

    op.execute('CREATE EXTENSION IF NOT EXISTS citext')
    op.alter_column(
        'users', 'email',
        existing_type=sa.String(length=320),
        type_=postgresql.CITEXT(),
        existing_nullable=False,
    )

    op.add_column('users', sa.Column(
        'status', sa.String(length=20),
        server_default='active', nullable=False,
    ))

    # Existing users get their first interview's time when they have
    # one, otherwise the migration time.
    op.add_column('users', sa.Column(
        'created_at', sa.DateTime(timezone=True),
        server_default=sa.text('now()'), nullable=False,
    ))
    op.add_column('users', sa.Column(
        'updated_at', sa.DateTime(timezone=True),
        server_default=sa.text('now()'), nullable=False,
    ))
    op.execute("""
        UPDATE users u
        SET created_at = first_interview.created_at,
            updated_at = first_interview.created_at
        FROM (
            SELECT user_id, min(created_at) AS created_at
            FROM interviews
            GROUP BY user_id
        ) AS first_interview
        WHERE first_interview.user_id = u.id
    """)

    # --- interviews --------------------------------------------------

    rename_constraint_if_exists(
        'interviews', 'interviews_pkey', 'pk_interviews',
    )
    rename_constraint_if_exists(
        'interviews', 'interviews_user_id_fkey', 'fk_interviews_user_id_users',
    )
    op.alter_column(
        'interviews', 'id',
        server_default=sa.text('gen_random_uuid()'),
    )
    op.alter_column(
        'interviews', 'created_at',
        server_default=sa.text('now()'),
    )

    op.add_column('interviews', sa.Column(
        'updated_at', sa.DateTime(timezone=True),
        server_default=sa.text('now()'), nullable=False,
    ))
    op.execute('UPDATE interviews SET updated_at = created_at')

    op.create_index(
        'ix_interviews_user_id_created_at', 'interviews',
        ['user_id', sa.literal_column('created_at DESC')],
    )

    # --- interview_answers (old table, dropped later) ----------------

    rename_constraint_if_exists(
        'interview_answers',
        'interview_answers_interview_id_fkey',
        'fk_interview_answers_interview_id_interviews',
    )
    rename_constraint_if_exists(
        'interview_answers', 'interview_answers_pkey', 'pk_interview_answers',
    )

    # --- new tables --------------------------------------------------

    op.create_table(
        'interview_attempts',
        sa.Column('interview_attempt_id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('interview_id', sa.Uuid(), nullable=False),
        sa.Column('attempt_number', sa.SmallInteger(), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='in_progress', nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['interview_id'], ['interviews.id'], name=op.f('fk_interview_attempts_interview_id_interviews'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('interview_attempt_id', name=op.f('pk_interview_attempts')),
        sa.UniqueConstraint('interview_id', 'attempt_number', name=op.f('uq_interview_attempts_interview_id_attempt_number')),
    )

    op.create_table(
        'interview_attempt_evaluations',
        sa.Column('interview_attempt_evaluation_id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('interview_attempt_id', sa.Uuid(), nullable=False),
        sa.Column('overall_score', sa.SmallInteger(), nullable=False),
        sa.Column('recommendation', sa.String(length=30), nullable=False),
        sa.Column('conclusion', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['interview_attempt_id'], ['interview_attempts.interview_attempt_id'], name=op.f('fk_interview_attempt_evaluations_interview_attempt_id_interview_attempts'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('interview_attempt_evaluation_id', name=op.f('pk_interview_attempt_evaluations')),
        sa.UniqueConstraint('interview_attempt_id', name=op.f('uq_interview_attempt_evaluations_interview_attempt_id')),
    )

    op.create_table(
        'questions',
        sa.Column('question_id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('interview_attempt_id', sa.Uuid(), nullable=False),
        sa.Column('position', sa.SmallInteger(), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=30), nullable=False),
        sa.Column('difficulty', sa.String(length=10), nullable=False),
        sa.Column('expected_topics', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['interview_attempt_id'], ['interview_attempts.interview_attempt_id'], name=op.f('fk_questions_interview_attempt_id_interview_attempts'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('question_id', name=op.f('pk_questions')),
        sa.UniqueConstraint('interview_attempt_id', 'position', name=op.f('uq_questions_interview_attempt_id_position')),
    )

    op.create_table(
        'answers',
        sa.Column('answer_id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('question_id', sa.Uuid(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['questions.question_id'], name=op.f('fk_answers_question_id_questions'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('answer_id', name=op.f('pk_answers')),
        sa.UniqueConstraint('question_id', name=op.f('uq_answers_question_id')),
    )

    op.create_table(
        'answer_evaluations',
        sa.Column('answer_evaluation_id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('answer_id', sa.Uuid(), nullable=False),
        sa.Column('score', sa.SmallInteger(), nullable=False),
        sa.Column('technical_accuracy', sa.SmallInteger(), nullable=False),
        sa.Column('relevance', sa.SmallInteger(), nullable=False),
        sa.Column('completeness', sa.SmallInteger(), nullable=False),
        sa.Column('communication', sa.SmallInteger(), nullable=False),
        sa.Column('feedback', sa.Text(), nullable=False),
        sa.Column('evaluation', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['answer_id'], ['answers.answer_id'], name=op.f('fk_answer_evaluations_answer_id_answers'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('answer_evaluation_id', name=op.f('pk_answer_evaluations')),
        sa.UniqueConstraint('answer_id', name=op.f('uq_answer_evaluations_answer_id')),
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_table('answer_evaluations')
    op.drop_table('answers')
    op.drop_table('questions')
    op.drop_table('interview_attempt_evaluations')
    op.drop_table('interview_attempts')

    # Constraint names are left in the new convention; the old schema
    # does not depend on them.

    op.drop_index('ix_interviews_user_id_created_at', table_name='interviews')
    op.drop_column('interviews', 'updated_at')
    op.alter_column('interviews', 'created_at', server_default=None)
    op.alter_column('interviews', 'id', server_default=None)

    op.drop_column('users', 'updated_at')
    op.drop_column('users', 'created_at')
    op.drop_column('users', 'status')
    op.alter_column(
        'users', 'email',
        existing_type=postgresql.CITEXT(),
        type_=sa.String(length=320),
        existing_nullable=False,
    )
    op.alter_column('users', 'id', server_default=None)
