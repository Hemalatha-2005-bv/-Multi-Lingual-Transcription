"""
Shared pytest fixtures for backend tests.
Uses an in-memory SQLite database so tests are isolated and fast.
"""

import asyncio
import sys
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Windows subprocess support
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# ── In-memory test database ───────────────────────────────────────────────────

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session")
async def setup_db():
    from app.core.database import Base
    import app.models.job  # noqa: F401 — register model
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(setup_db):
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def job_repo(db_session):
    from app.repositories.job_repository import JobRepository
    return JobRepository(db_session)


@pytest_asyncio.fixture
async def client(setup_db):
    """HTTPX async client wired to the FastAPI app with test DB."""
    import app.core.database as db_module
    db_module.AsyncSessionLocal = TestSessionLocal  # patch to use test DB

    # Stub out Whisper loading so tests don't require the model
    import app.infrastructure.whisper as w
    w._model = object()  # truthy sentinel

    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
