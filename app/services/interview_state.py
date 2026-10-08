from uuid import UUID, uuid4
from app.schemas.interview import InterviewQuestion

class InterviewSession:
    def __init__(
            self, 
            resume_text: str,
            job_description: str,
            questions: list[InterviewQuestion]
        ):
        self.resume_text = resume_text
        self.job_description = job_description
        self.questions = questions
        self.answers: dict[int, str] = {}

_interviews: dict[UUID, InterviewSession] = {}

def create_interview(
    resume_text: str,
    job_description: str,
    questions: list[InterviewQuestion]
) -> UUID:
    interview_id = uuid4()
    session = InterviewSession(resume_text, job_description, questions)
    _interviews[interview_id] = session
    return interview_id

def get_interview(
        interview_id: UUID
    ) -> InterviewSession | None:
    return _interviews.get(interview_id)

def save_answer(
        interview_id: UUID,
        question_id: int,
        answer: str
    ) -> None:
    session = _interviews.get(interview_id)
    if not session:
        raise ValueError("Interview session not found.")

    question_exists = any(q.id == question_id for q in session.questions)
    if not question_exists:
        raise ValueError("Question does not belong to this interview.")
    
    session.answers[question_id] = answer
