"""copy interviews into attempts, questions, answers and evaluations

Data step: each existing interview becomes attempt #1 of itself. Only
inserts into the new tables; the old columns and interview_answers are
left untouched, so downgrading just empties the new tables.

Only interviews without an attempt are copied, so the contract revision
can run the same copy again to pick up interviews created by the old code
after this ran. The checks at the end stop the migration (and roll it all
back) if anything was not copied.

Revision ID: 943dab65b4f8
Revises: 70750a06dc62
Create Date: 2026-10-23 08:22:52.051721

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '943dab65b4f8'
down_revision: Union[str, Sequence[str], None] = '70750a06dc62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COPY_STATEMENTS = [
    # Attempts created by this run, so the steps below only touch them.
    """
    CREATE TEMPORARY TABLE copied_attempts (
        interview_attempt_id uuid PRIMARY KEY,
        interview_id uuid NOT NULL UNIQUE
    ) ON COMMIT DROP
    """,

    # 1. One attempt per interview. The completion time was never
    #    stored, so completed attempts use the interview's created_at.
    """
    WITH inserted AS (
        INSERT INTO interview_attempts (
            interview_id, attempt_number, status,
            completed_at, created_at, updated_at
        )
        SELECT
            i.id,
            1,
            lower(i.status::text),
            CASE WHEN i.status::text = 'COMPLETED' THEN i.created_at END,
            i.created_at,
            i.created_at
        FROM interviews i
        WHERE NOT EXISTS (
            SELECT 1 FROM interview_attempts a
            WHERE a.interview_id = i.id
        )
        RETURNING interview_attempt_id, interview_id
    )
    INSERT INTO copied_attempts
    SELECT interview_attempt_id, interview_id FROM inserted
    """,

    # 2. Questions from the interviews.questions JSON array. The item's
    #    "id" (1..5) is what the API calls question_id.
    """
    INSERT INTO questions (
        interview_attempt_id, position, question, category,
        difficulty, expected_topics, created_at
    )
    SELECT
        c.interview_attempt_id,
        (q.item->>'id')::smallint,
        q.item->>'question',
        q.item->>'category',
        q.item->>'difficulty',
        q.item->'expected_topics',
        i.created_at
    FROM copied_attempts c
    JOIN interviews i ON i.id = c.interview_id
    CROSS JOIN LATERAL jsonb_array_elements(i.questions::jsonb) AS q(item)
    """,

    # 3. Answers, matched to their question by position. Old answers
    #    have no timestamps, so they use the interview's created_at.
    """
    INSERT INTO answers (question_id, answer, created_at, updated_at)
    SELECT q.question_id, ia.answer, i.created_at, i.created_at
    FROM copied_attempts c
    JOIN interviews i ON i.id = c.interview_id
    JOIN interview_answers ia ON ia.interview_id = c.interview_id
    JOIN questions q
        ON q.interview_attempt_id = c.interview_attempt_id
       AND q.position = ia.question_id
    """,

    # 4. Per-answer evaluations: sub-scores and feedback become columns,
    #    the lists stay JSON.
    """
    INSERT INTO answer_evaluations (
        answer_id, score, technical_accuracy, relevance, completeness,
        communication, feedback, evaluation, created_at
    )
    SELECT
        a.answer_id,
        ia.score,
        (ia.evaluation->>'technical_accuracy')::smallint,
        (ia.evaluation->>'relevance')::smallint,
        (ia.evaluation->>'completeness')::smallint,
        (ia.evaluation->>'communication')::smallint,
        ia.evaluation->>'feedback',
        jsonb_build_object(
            'evidence', ia.evaluation::jsonb->'evidence',
            'strengths', ia.evaluation::jsonb->'strengths',
            'weaknesses', ia.evaluation::jsonb->'weaknesses'
        ),
        i.created_at
    FROM copied_attempts c
    JOIN interviews i ON i.id = c.interview_id
    JOIN interview_answers ia ON ia.interview_id = c.interview_id
    JOIN questions q
        ON q.interview_attempt_id = c.interview_attempt_id
       AND q.position = ia.question_id
    JOIN answers a ON a.question_id = q.question_id
    WHERE ia.evaluation IS NOT NULL
    """,

    # 5. Overall result of completed interviews.
    """
    INSERT INTO interview_attempt_evaluations (
        interview_attempt_id, overall_score, recommendation,
        conclusion, created_at
    )
    SELECT
        c.interview_attempt_id,
        i.overall_score,
        i.recommendation,
        i.conclusion,
        i.created_at
    FROM copied_attempts c
    JOIN interviews i ON i.id = c.interview_id
    WHERE i.status::text = 'COMPLETED'
    """,
]

# Each query counts rows that were not copied; all must return 0.
CHECKS = {
    "interviews without an attempt": """
        SELECT count(*) FROM interviews i
        WHERE NOT EXISTS (
            SELECT 1 FROM interview_attempts a WHERE a.interview_id = i.id
        )
    """,
    "attempts whose question count differs from the JSON": """
        SELECT count(*) FROM copied_attempts c
        JOIN interviews i ON i.id = c.interview_id
        WHERE json_array_length(i.questions) <> (
            SELECT count(*) FROM questions q
            WHERE q.interview_attempt_id = c.interview_attempt_id
        )
    """,
    "old answers without a matching question": """
        SELECT count(*) FROM copied_attempts c
        JOIN interview_answers ia ON ia.interview_id = c.interview_id
        WHERE NOT EXISTS (
            SELECT 1 FROM questions q
            JOIN answers a ON a.question_id = q.question_id
            WHERE q.interview_attempt_id = c.interview_attempt_id
              AND q.position = ia.question_id
        )
    """,
    "old evaluations not copied": """
        SELECT count(*) FROM copied_attempts c
        JOIN interview_answers ia ON ia.interview_id = c.interview_id
        JOIN questions q
            ON q.interview_attempt_id = c.interview_attempt_id
           AND q.position = ia.question_id
        JOIN answers a ON a.question_id = q.question_id
        WHERE ia.evaluation IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM answer_evaluations e
              WHERE e.answer_id = a.answer_id
          )
    """,
    "completed attempts without an evaluation": """
        SELECT count(*) FROM copied_attempts c
        JOIN interview_attempts a
            ON a.interview_attempt_id = c.interview_attempt_id
        WHERE a.status = 'completed'
          AND NOT EXISTS (
              SELECT 1 FROM interview_attempt_evaluations e
              WHERE e.interview_attempt_id = c.interview_attempt_id
          )
    """,
}


def upgrade() -> None:
    """Upgrade schema."""

    # New code stops writing these old columns before they are dropped.
    op.alter_column('interviews', 'questions', existing_type=sa.JSON(), nullable=True)
    op.alter_column(
        'interviews', 'status',
        existing_type=sa.Enum('IN_PROGRESS', 'COMPLETED', name='interviewstatus'),
        nullable=True,
    )

    bind = op.get_bind()

    for statement in COPY_STATEMENTS:
        bind.execute(sa.text(statement))

    failures = {
        name: count
        for name, query in CHECKS.items()
        if (count := bind.execute(sa.text(query)).scalar_one())
    }

    if failures:
        raise RuntimeError(f'Interview copy is incomplete: {failures}')


# Reverse copy for downgrade: attempt #1 back into the old columns, so
# nothing written by the new code is lost if the old code comes back.
RESTORE_STATEMENTS = [
    """
    DELETE FROM interview_answers ia
    USING interview_attempts a
    WHERE a.interview_id = ia.interview_id AND a.attempt_number = 1
    """,
    """
    INSERT INTO interview_answers (
        id, interview_id, question_id, answer, score, evaluation
    )
    SELECT
        gen_random_uuid(),
        a.interview_id,
        q.position,
        ans.answer,
        ev.score,
        CASE WHEN ev.answer_evaluation_id IS NOT NULL THEN (
            jsonb_build_object(
                'question_id', q.position,
                'technical_accuracy', ev.technical_accuracy,
                'relevance', ev.relevance,
                'completeness', ev.completeness,
                'communication', ev.communication,
                'feedback', ev.feedback
            ) || ev.evaluation
        )::json END
    FROM interview_attempts a
    JOIN questions q ON q.interview_attempt_id = a.interview_attempt_id
    JOIN answers ans ON ans.question_id = q.question_id
    LEFT JOIN answer_evaluations ev ON ev.answer_id = ans.answer_id
    WHERE a.attempt_number = 1
    """,
    """
    UPDATE interviews i
    SET
        questions = coalesce(i.questions, (
            SELECT json_agg(json_build_object(
                'id', q.position,
                'question', q.question,
                'category', q.category,
                'difficulty', q.difficulty,
                'expected_topics', q.expected_topics
            ) ORDER BY q.position)
            FROM questions q
            WHERE q.interview_attempt_id = a.interview_attempt_id
        )),
        status = upper(a.status)::interviewstatus,
        overall_score = e.overall_score,
        recommendation = e.recommendation,
        conclusion = e.conclusion,
        evaluation_summary = CASE WHEN e.interview_attempt_id IS NOT NULL THEN
            coalesce(i.evaluation_summary, json_build_object(
                'interview_id', i.id,
                'overall_score', e.overall_score,
                'recommendation', e.recommendation,
                'conclusion', e.conclusion,
                'total_questions', (
                    SELECT count(*) FROM questions q
                    WHERE q.interview_attempt_id = a.interview_attempt_id
                ),
                'question_results', (
                    SELECT json_agg(json_build_object(
                        'question_id', q.position,
                        'score', ev.score,
                        'technical_accuracy', ev.technical_accuracy,
                        'relevance', ev.relevance,
                        'completeness', ev.completeness,
                        'communication', ev.communication,
                        'evidence', ev.evaluation->'evidence',
                        'strengths', ev.evaluation->'strengths',
                        'weaknesses', ev.evaluation->'weaknesses',
                        'feedback', ev.feedback
                    ) ORDER BY q.position)
                    FROM questions q
                    JOIN answers ans ON ans.question_id = q.question_id
                    JOIN answer_evaluations ev ON ev.answer_id = ans.answer_id
                    WHERE q.interview_attempt_id = a.interview_attempt_id
                )
            ))
        END
    FROM interview_attempts a
    LEFT JOIN interview_attempt_evaluations e
        ON e.interview_attempt_id = a.interview_attempt_id
    WHERE a.interview_id = i.id AND a.attempt_number = 1
    """,
]


def downgrade() -> None:
    """Downgrade schema."""

    bind = op.get_bind()

    for statement in RESTORE_STATEMENTS:
        bind.execute(sa.text(statement))

    # Cascades to questions, answers and both evaluation tables.
    op.execute('DELETE FROM interview_attempts')

    op.alter_column(
        'interviews', 'status',
        existing_type=sa.Enum('IN_PROGRESS', 'COMPLETED', name='interviewstatus'),
        nullable=False,
    )
    op.alter_column('interviews', 'questions', existing_type=sa.JSON(), nullable=False)
