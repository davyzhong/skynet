"""Base connector interface for data ingestion."""

from abc import ABC, abstractmethod
from typing import Any

import polars as pl


class BaseConnector(ABC):
    """Abstract base class for data source connectors."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the data source."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the data source."""
        pass

    @abstractmethod
    async def fetch_all(self, query: str) -> pl.DataFrame:
        """Fetch all data from a query."""
        pass

    @abstractmethod
    async def fetch_incremental(self, query: str, last_value: Any) -> pl.DataFrame:
        """Fetch incremental data based on last sync value."""
        pass

    async def __aenter__(self) -> "BaseConnector":
        """Context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        await self.disconnect()
