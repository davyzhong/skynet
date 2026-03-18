"""Connector factory for creating appropriate connector instances."""

from app.ingestion.connectors.api import APIConnector
from app.ingestion.connectors.base import BaseConnector
from app.ingestion.connectors.file import FileConnector
from app.ingestion.connectors.postgresql import PostgreSQLConnector


class ConnectorFactory:
    """Factory for creating data source connectors."""

    @staticmethod
    def create(config: dict) -> BaseConnector:
        """Create a connector based on source type."""
        source_type = config.get("type", "").lower()

        if source_type == "postgresql":
            return PostgreSQLConnector.from_config(config)
        elif source_type == "mysql":
            return PostgreSQLConnector.from_config(config)  # Reuse PostgreSQL connector
        elif source_type == "file":
            return FileConnector.from_config(config)
        elif source_type == "api":
            return APIConnector.from_config(config)
        else:
            raise ValueError(f"Unknown source type: {source_type}")
