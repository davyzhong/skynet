"""Repository pattern for data access."""

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.storage.models import (
    Alert,
    AlertHistory,
    DataSource,
    Metric,
    MetricValue,
    Report,
    ReportExecution,
    SyncJob,
)

settings = get_settings()

engine = create_async_engine(settings.database.url, echo=False, pool_pre_ping=True)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database session."""
    async for session in get_session():
        yield session


T = TypeVar("T")


class BaseRepository:
    """Base repository with common CRUD operations."""

    model: type[T]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, id: int) -> T | None:
        """Find entity by ID."""
        result = await self.session.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def find_all(self) -> list[T]:
        """Find all entities."""
        result = await self.session.execute(select(self.model))
        return list(result.scalars().all())

    async def create(self, **kwargs: Any) -> T:
        """Create a new entity."""
        entity = self.model(**kwargs)
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, id: int, **kwargs: Any) -> T | None:
        """Update an entity by ID."""
        entity = await self.find_by_id(id)
        if entity is None:
            return None
        for key, value in kwargs.items():
            setattr(entity, key, value)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, id: int) -> bool:
        """Delete an entity by ID."""
        entity = await self.find_by_id(id)
        if entity is None:
            return False
        await self.session.delete(entity)
        await self.session.flush()
        return True


class DataSourceRepository(BaseRepository):
    """Repository for DataSource entities."""

    model = DataSource


class SyncJobRepository(BaseRepository):
    """Repository for SyncJob entities."""

    model = SyncJob


class MetricRepository(BaseRepository):
    """Repository for Metric entities."""

    model = Metric


class MetricValueRepository(BaseRepository):
    """Repository for MetricValue entities."""

    model = MetricValue


class ReportRepository(BaseRepository):
    """Repository for Report entities."""

    model = Report


class ReportExecutionRepository(BaseRepository):
    """Repository for ReportExecution entities."""

    model = ReportExecution


class AlertRepository(BaseRepository):
    """Repository for Alert entities."""

    model = Alert


class AlertHistoryRepository(BaseRepository):
    """Repository for AlertHistory entities."""

    model = AlertHistory
