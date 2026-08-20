"""
Database connection and session management.
"""

import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from loguru import logger

from app.core.config import get_settings
from app.models.database import Base

settings = get_settings()

# Ensure database directory exists for SQLite
if "sqlite" in settings.database_url:
    # Extract database path from SQLite URL
    # Format: sqlite+aiosqlite:///path (relative, 3 slashes)
    #         sqlite+aiosqlite:////path (absolute, 4 slashes)
    if settings.database_url.startswith("sqlite+aiosqlite:////"):
        # Absolute path: remove scheme + 3 slashes, leaving /absolute/path
        db_path = settings.database_url[len("sqlite+aiosqlite:///"):]
    else:
        # Relative path: remove scheme + 3 slashes
        db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"Ensured database directory exists: {db_dir}")

# Create async engine
if "sqlite" in settings.database_url:
    # SQLite specific settings
    engine = create_async_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.debug,
    )
else:
    # PostgreSQL or other databases
    engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
        pool_pre_ping=True,
    )

# Create session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db():
    """Initialize database tables in development/test only.

    Production deployments must run Alembic migrations instead of letting the
    application mutate schema at startup.
    """
    if settings.is_production:
        logger.info("Skipping create_all in production; run Alembic migrations before startup")
        return

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
