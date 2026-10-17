"""Database connection and session factory management module.

Configures:
1. An asynchronous SQLAlchemy engine and sessionmaker (`AsyncSessionLocal`)
   for high-concurrency, non-blocking FastAPI request handling.
2. A synchronous SQLAlchemy engine and sessionmaker (`SyncSessionLocal`)
   optimized for Celery background tasks and migration operations.
3. Declarative Base for ORM entity mapping.
"""

from typing import AsyncGenerator, Generator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings

# ------------------------------------------------------------------------------
# Asynchronous Database Engine & Session Factory (FastAPI REST Endpoints)
# ------------------------------------------------------------------------------
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# ------------------------------------------------------------------------------
# Synchronous Database Engine & Session Factory (Celery Workers)
# ------------------------------------------------------------------------------
sync_engine = create_engine(
    settings.SYNC_DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)

# Declarative Base for ORM Models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide an asynchronous database session for FastAPI dependency injection.

    Yields:
        AsyncSession: An active asynchronous database session that closes automatically.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_sync_db() -> Generator[Session, None, None]:
    """Provide a synchronous database session context for background workers.

    Yields:
        Session: An active synchronous SQLAlchemy session that closes automatically.
    """
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()
