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
import hashlib
import secrets
from uuid import UUID

from authlib.integrations.starlette_client import OAuthError
from fastapi import Request
from fastapi.responses import RedirectResponse

from app.services.google_oauth import oauth
from app.services.redis_client import redis_client
from app.config import settings
from sqlalchemy import select
from pydantic import BaseModel, Field

class GoogleCodeExchange(BaseModel):
    code: str = Field(min_length=20, max_length=200)


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
        id=current_user.user_id,
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
        id=user.user_id,
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

    if user is None or user.password_hash is None:
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
        user.user_id
    )

    return TokenResponse(
        access_token=access_token,
    )

@router.get("/google/login")
async def google_login(request: Request):
    client = oauth.create_client("google")
    return await client.authorize_redirect(
        request,
        settings.google_redirect_uri,
    )

@router.get("/google/callback")
async def google_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    client = oauth.create_client("google")

    try:
        token = await client.authorize_access_token(request)
        user_info = token.get("userinfo")

        if not user_info:
            return RedirectResponse(
                f"{settings.frontend_url}/login?error=google_login_failed"
            )

        google_sub = user_info.get("sub")
        email = user_info.get("email")

        if (
            not google_sub
            or not email
            or user_info.get("email_verified") is not True
        ):
            return RedirectResponse(
                f"{settings.frontend_url}/login?error=google_email_unverified"
            )

        email = email.strip().lower()

        result = await db.execute(
            select(UserModel).where(
                UserModel.google_sub == google_sub
            )
        )
        user = result.scalar_one_or_none()

        if user is None:
            existing = await get_user_by_email(db, email)

            # Never silently link an existing account by email alone.
            if existing is not None:
                return RedirectResponse(
                    f"{settings.frontend_url}/login?error=account_exists"
                )

            user = await create_user(
                db=db,
                email=email,
                password_hash=None,
                google_sub=google_sub,
            )

        if user.status != UserStatus.ACTIVE:
            return RedirectResponse(
                f"{settings.frontend_url}/login?error=account_disabled"
            )

        code = secrets.token_urlsafe(32)
        code_hash = hashlib.sha256(code.encode()).hexdigest()

        await redis_client.set(
            f"google-login:{code_hash}",
            str(user.user_id),
            ex=60,
            nx=True,
        )

        return RedirectResponse(
            f"{settings.frontend_url}/auth/google/callback?code={code}",
            status_code=302,
        )

    except OAuthError:
        return RedirectResponse(
            f"{settings.frontend_url}/login?error=google_login_failed"
        )

@router.post("/google/exchange", response_model=TokenResponse)
async def google_exchange(request: GoogleCodeExchange):
    code_hash = hashlib.sha256(request.code.encode()).hexdigest()

    user_id = await redis_client.getdel(
        f"google-login:{code_hash}"
    )

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login code is invalid or expired.",
        )

    try:
        access_token = create_access_token(UUID(user_id))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login code.",
        )

    return TokenResponse(access_token=access_token)