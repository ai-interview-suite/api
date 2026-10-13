from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.interview_repository import (
    create_interview,
    get_user_interview,
    save_interview_answer
)
from app.dependencies import get_current_user
from app.models.user import UserModel
from app.models.interview import InterviewStatus
from app.schemas.interview import InterviewAnswerRequest, InterviewStartResponse, InterviewResultResponse
from app.services.ai_service import generate_interview_questions
from app.services.exceptions import AIResponseValidationError, AIServiceUnavailableError
from app.services.resume_parser import extract_text_from_pdf
from app.services.interview_completion import complete_interview


router = APIRouter(
    prefix="/interview",
    tags=["interview"]
)

@router.post(
    "/start",
    response_model=InterviewStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_interview(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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

    interview = await create_interview(
        db=db,
        user_id = current_user.id,
        resume_text = resume_text,
        job_description = job_description,
        questions = questions.questions
    )

    return InterviewStartResponse(
        interview_id=interview.id,
        questions=questions.questions,
    )

@router.post("/{interview_id}/answers")
async def submit_answer(
    interview_id: UUID,
    request: InterviewAnswerRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    interview = await get_user_interview(
        db=db,
        interview_id=interview_id,
        user_id=current_user.id,
    )

    if interview is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found.",
        )

    try:
        await save_interview_answer(
            db=db,
            interview=interview,
            question_id=request.question_id,
            answer=request.answer,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return {
        "message": "Answer saved successfully.",
        "interview_id": interview.id,
        "question_id": request.question_id
    }

@router.get("/{interview_id}")
async def get_interview_status(
    interview_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    interview = await get_user_interview(
        db=db,
        interview_id=interview_id,
        user_id=current_user.id,
    )

    if interview is None:
        raise HTTPException(
            status_code=404,
            detail="Interview not found.",
        )

    total_questions = len(interview.questions)
    answered_questions = len(interview.answers)

    return {
        "interview_id": interview_id,
        "total_questions": total_questions,
        "answered_questions": answered_questions,
        "completed": interview.status == InterviewStatus.COMPLETED
    }

@router.post(
    "/{interview_id}/submit", 
    response_model=InterviewResultResponse
)
async def submit_interview(
    interview_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await complete_interview(
            db=db,
            interview_id=interview_id,
            user_id=current_user.id,
        )
    except LookupError:
        raise HTTPException(
            status_code=404,
            detail="Interview not found.",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
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

@router.get(
    "/{interview_id}/result",
    response_model=InterviewResultResponse,
)
async def get_interview_result(
    interview_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    interview = await get_user_interview(
        db=db,
        interview_id=interview_id,
        user_id=current_user.id,
    )

    if interview is None:
        raise HTTPException(
            status_code=404,
            detail="Interview not found.",
        )

    if interview.status != InterviewStatus.COMPLETED:
        raise HTTPException(
            status_code=409,
            detail="Interview has not been completed.",
        )

    if interview.evaluation_summary is None:
        raise HTTPException(
            status_code=500,
            detail="Interview result is unavailable.",
        )

    return InterviewResultResponse.model_validate(
        interview.evaluation_summary
    )