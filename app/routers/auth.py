from fastapi import APIRouter, HTTPException, status, Depends

from app.dependencies import get_current_user
from app.services.user_state import User
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
from app.services.user_state import (
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
    current_user: User = Depends(
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
)
async def register(
    request: UserCreate,
):

    existing_user = get_user_by_email(
        request.email
    )

    if existing_user is not None:
        raise HTTPException(
            status_code=409,
            detail="Email is already registered.",
        )

    password_hash = hash_password(
        request.password
    )

    user = create_user(
        email=request.email,
        password_hash=password_hash,
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
):

    user = get_user_by_email(
        request.email
    )

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

    access_token = create_access_token(
        user.id
    )

    return TokenResponse(
        access_token=access_token,
    )