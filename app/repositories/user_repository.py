from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserModel


async def get_user_by_email(
    db: AsyncSession,
    email: str,
) -> UserModel | None:
    normalized_email = email.strip().lower()

    result = await db.execute(
        select(UserModel).where(
            UserModel.email == normalized_email
        )
    )

    return result.scalar_one_or_none()

async def get_user_by_id(
    db: AsyncSession,
    user_id: UUID,
) -> UserModel | None:

    result = await db.execute(
        select(UserModel).where(
            UserModel.user_id == user_id
        )
    )

    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    email: str,
    password_hash: str,
) -> UserModel:
    user = UserModel(
        email=email.strip().lower(),
        password_hash=password_hash,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user