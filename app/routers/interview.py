from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.dependencies import get_current_user
from app.schemas.interview import InterviewAnswerRequest, InterviewStartResponse, InterviewResultResponse
from app.services.ai_service import generate_interview_questions, evaluate_interview
from app.services.exceptions import AIResponseValidationError, AIServiceUnavailableError
from app.services.resume_parser import extract_text_from_pdf
from app.services.interview_state import create_interview, save_answer
from app.services.scoring import calculate_overall_score, build_question_results
from app.services.result_service import get_recommendation, build_conclusion
from app.services.user_state import User
from app.services.interview_access import (
    get_user_interview,
    InterviewAccessDeniedError,
    InterviewNotFoundError,
)


router = APIRouter(
    prefix="/interview",
    tags=["interview"]
)

@router.post(
    "/start",
    response_model=InterviewStartResponse,
)
async def start_interview(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
    current_user: User = Depends(get_current_user),
):
    if resume.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF files are allowed.",
        )
    
    file_content = await resume.read()
    resume_text = extract_text_from_pdf(file_content)
    if not resume_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to extract text from the uploaded PDF.",
        )

    try:
        questions = await generate_interview_questions(
            resume_text=resume_text,
            job_description=job_description,
        )

        interview_id = create_interview(
            user_id = current_user.id,
            resume_text = resume_text,
            job_description = job_description,
            questions = questions.questions
        )
    except AIServiceUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is temporarily unavailable.",
        )
    except AIResponseValidationError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI returned an invalid response.",
        )

    return InterviewStartResponse(
        interview_id=interview_id,
        questions=questions.questions,
    )

@router.post("/{interview_id}/answers")
async def submit_answer(
    interview_id: UUID,
    request: InterviewAnswerRequest,
    current_user: User = Depends(get_current_user)
):
    try:
        interview = get_user_interview(
            interview_id=interview_id,
            user_id=current_user.id,
        )
        
        save_answer(
            interview_id=interview_id,
            question_id=request.question_id,
            answer=request.answer,
        )
    except InterviewNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found.",
        )
    except InterviewAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this interview.",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return {
        "message": "Answer saved successfully.",
        "interview_id": interview_id,
        "question_id": request.question_id
    }

@router.get("/{interview_id}")
async def get_interview_status(
    interview_id: UUID,
    current_user: User = Depends(get_current_user)
):
    try:
        interview = get_user_interview(
            interview_id=interview_id,
            user_id=current_user.id,
        )
    except InterviewNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found.",
            )
    except InterviewAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this interview.",
        )

    total_questions = len(interview.questions)
    answered_questions = len(interview.answers)

    return {
        "interview_id": interview_id,
        "total_questions": total_questions,
        "answered_questions": answered_questions,
        "completed": total_questions == answered_questions
    }

@router.post("/{interview_id}/submit", response_model=InterviewResultResponse)
async def submit_interview(
    interview_id: UUID,
    current_user: User = Depends(get_current_user)
):
    try:
        interview = get_user_interview(
            interview_id=interview_id,
            user_id=current_user.id,
        )
    except InterviewNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found.",
            )
    except InterviewAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this interview.",
        )

    total_questions = len(interview.questions)
    answered_questions = len(interview.answers)

    if answered_questions != total_questions:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Please answer all questions. "
                f"{answered_questions}/{total_questions} answered."
            ),
        )

    try:
        evaluation = await evaluate_interview(
            resume_text=interview.resume_text,
            job_description=interview.job_description,
            questions=interview.questions,
            answers=interview.answers,
        )

    except AIServiceUnavailableError:
        raise HTTPException(
            status_code=503,
            detail="AI service is temporarily unavailable.",
        )

    except AIResponseValidationError:
        raise HTTPException(
            status_code=502,
            detail="AI returned an invalid response.",
        )

    overall_score = calculate_overall_score(
        evaluation.evaluations
    )

    recommendation = get_recommendation(
        overall_score
    )

    conclusion = build_conclusion(
        score=overall_score,
        recommendation=recommendation,
    )

    question_results = build_question_results(
        evaluation.evaluations
    )

    return InterviewResultResponse(
        interview_id=interview_id,
        overall_score=overall_score,
        recommendation=recommendation,
        conclusion=conclusion,
        total_questions=total_questions,
        question_results=question_results,
    )