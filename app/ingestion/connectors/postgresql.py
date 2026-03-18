"""PostgreSQL connector implementation."""

from typing import Any

import polars as pl
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.ingestion.connectors.base import BaseConnector


class PostgreSQLConnector(BaseConnector):
    """Connector for PostgreSQL databases."""

    def __init__(self, host: str, port: int, database: str, user: str, password: str):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker | None = None

    async def connect(self) -> None:
        """Establish connection to PostgreSQL."""
        url = f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        self._engine = create_async_engine(url, pool_pre_ping=True, pool_size=5)
        self._session_factory = async_sessionmaker(
            self._engine, expire_on_commit=False
        )

    async def disconnect(self) -> None:
        """Close PostgreSQL connection."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

    async def fetch_all(self, query: str, chunk_size: int = 10000) -> pl.DataFrame:
        """Fetch all data with chunked reading."""
        if not self._session_factory:
            raise RuntimeError("Not connected. Call connect() first.")

        frames = []
        async with self._session_factory() as session:
            result = await session.stream(text(query))
            while True:
                chunk = await result.fetchmany(chunk_size)
                if not chunk:
                    break
                rows = [dict(row._mapping) for row in chunk]
                if rows:
                    frames.append(pl.DataFrame(rows))

        if not frames:
            return pl.DataFrame()

        return pl.concat(frames) if len(frames) > 1 else frames[0]

    async def fetch_incremental(
        self, query: str, last_value: Any, key_field: str = "id"
    ) -> pl.DataFrame:
        """Fetch incremental data using WHERE clause."""
        if not self._session_factory:
            raise RuntimeError("Not connected. Call connect() first.")

        incremental_query = f"{query.rstrip(';')} WHERE {key_field} > :last_value"
        async with self._session_factory() as session:
            result = await session.execute(text(incremental_query), {"last_value": last_value})
            rows = [dict(row._mapping) for row in result.fetchall()]

        if not rows:
            return pl.DataFrame()

        return pl.DataFrame(rows)

    @classmethod
    def from_config(cls, config: dict) -> "PostgreSQLConnector":
        """Create connector from configuration dictionary."""
        return cls(
            host=config.get("host", "localhost"),
            port=config.get("port", 5432),
            database=config["database"],
            user=config["user"],
            password=config["password"],
        )
