import os
from collections.abc import AsyncGenerator
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from dotenv import load_dotenv

# Load the test environment before importing the app, so that
# app.config.settings (and app.database.engine) also point at the
# test database instead of the development one from .env.
load_dotenv(
    Path(__file__).resolve().parent.parent / ".env.test",
    override=True,
)

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.database import get_db
from app.dependencies import get_current_user
from app.main import app
from app.models import Base
from app.models.user import UserModel


TEST_DATABASE_URL = os.environ.get("DATABASE_URL")

if not TEST_DATABASE_URL:
    raise RuntimeError(
        "Set DATABASE_URL in .env.test before running tests."
    )

if "test" not in TEST_DATABASE_URL.rsplit("/", 1)[-1].lower():
    raise RuntimeError(
        "DATABASE_URL in .env.test must point to a test database."
    )


# pytest-asyncio gives each test its own event loop, so pooled
# connections cannot be reused across tests.
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture
async def test_db():
    async with test_engine.begin() as connection:
        await connection.run_sync(
            Base.metadata.create_all
        )

    yield

    async with test_engine.begin() as connection:
        await connection.run_sync(
            Base.metadata.drop_all
        )


@pytest_asyncio.fixture
async def test_user_id(test_db) -> UUID:
    async with TestSessionLocal() as session:
        user = UserModel(
            email="test-user@example.com",
            password_hash="$2b$12$test-placeholder",
        )

        session.add(user)
        await session.commit()
        await session.refresh(user)

        return user.id


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def anonymous_client(
    test_db,
) -> AsyncGenerator[AsyncClient, None]:
    """Client using the real authentication flow."""

    app.dependency_overrides[get_db] = override_get_db

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(
    test_db,
    test_user_id: UUID,
) -> AsyncGenerator[AsyncClient, None]:
    """Client already authenticated as the test user."""

    async def override_get_current_user():
        return SimpleNamespace(
            id=test_user_id,
            email="test-user@example.com",
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = (
        override_get_current_user
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session