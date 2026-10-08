from uuid import UUID

from app.services.interview_state import (
    InterviewSession,
    get_interview,
)


class InterviewNotFoundError(Exception):
    pass


class InterviewAccessDeniedError(Exception):
    pass


def get_user_interview(
    interview_id: UUID,
    user_id: UUID,
) -> InterviewSession:

    interview = get_interview(
        interview_id
    )

    if interview is None:
        raise InterviewNotFoundError(
            "Interview not found."
        )

    if interview.user_id != user_id:
        raise InterviewAccessDeniedError(
            "You do not have access to this interview."
        )

    return interview