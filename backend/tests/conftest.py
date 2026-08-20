"""
Pytest configuration and fixtures for Campus Assistant tests.
"""

import asyncio
import os
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment before importing app
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["ADMIN_PASSWORD_HASH"] = "$2b$12$.8rTB.T6wG/8iv5ma1BTkOPTXDcrbjwcKl1s2vCUVdP5zPnp59nWW"  # dev-password-change-me

from app.main import app
from app.core.database import get_db
from app.models.database import Base


# Create test database engine
test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing endpoints."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def admin_auth_header() -> dict:
    """Return admin authentication header for protected endpoints."""
    import base64
    credentials = base64.b64encode(b"admin:dev-password-change-me").decode("utf-8")
    return {"Authorization": f"Basic {credentials}"}


@pytest.fixture
def sample_faq_data() -> dict:
    """Sample FAQ data for testing."""
    return {
        "question": "What is the fee structure?",
        "answer": "The annual fee is INR 50,000 including tuition.",
        "category": "fees",
        "language": "en",
    }


@pytest.fixture
def sample_chat_request() -> dict:
    """Sample chat request for testing."""
    return {
        "message": "What are the hostel fees?",
        "language": "en",
    }
