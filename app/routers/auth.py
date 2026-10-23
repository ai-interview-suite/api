from fastapi import APIRouter, HTTPException, status, Depends

from app.dependencies import get_current_user
from app.models.user import UserModel, UserStatus
from app.schemas.auth import (
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services.auth import create_access_token
from app.services.password import (
    hash_password,
    verify_password,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.repositories.user_repository import (
    create_user,
    get_user_by_email,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

@router.get(
    "/me",
    response_model=UserResponse,
)
async def get_me(
    current_user: UserModel = Depends(
        get_current_user
    ),
):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
    )

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
async def register(
    request: UserCreate,
    db: AsyncSession = Depends(get_db),
):

    email = str(request.email).strip().lower()
    existing_user = await get_user_by_email(
        db,
        email,
    )

    if existing_user is not None:
        raise HTTPException(
            status_code=409,
            detail="Email is already registered.",
        )

    password_hash = hash_password(
        request.password
    )

    try:
        user = await create_user(
            db=db,
            email=email,
            password_hash=password_hash,
        )
    except IntegrityError:
        # A concurrent registration may have inserted
        # this email after our initial lookup.
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered.",
        )

    return UserResponse(
        id=user.id,
        email=user.email,
    )

@router.post(
    "/login",
    response_model=TokenResponse,
)
async def login(
    request: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    email = str(request.email).strip().lower()
    user = await get_user_by_email(db, email)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    password_valid = verify_password(
        request.password,
        user.password_hash,
    )

    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled.",
        )

    access_token = create_access_token(
        user.id
    )

    return TokenResponse(
        access_token=access_token,
    )