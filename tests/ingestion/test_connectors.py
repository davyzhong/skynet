"""Tests for data connectors."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl

from app.ingestion.connectors.base import BaseConnector
from app.ingestion.connectors.file import FileConnector
from app.ingestion.connectors.postgresql import PostgreSQLConnector


class TestFileConnector:
    """Tests for FileConnector."""

    @pytest.fixture
    def sample_csv_file(self, tmp_path):
        """Create a sample CSV file."""
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("id,name,value\n1,Alice,100\n2,Bob,200\n3,Charlie,150")
        return str(csv_path)

    @pytest.mark.asyncio
    async def test_connect_and_fetch_csv(self, sample_csv_file):
        """Test connecting and reading a CSV file."""
        connector = FileConnector(sample_csv_file)
        await connector.connect()

        assert connector._file_type == "csv"

        df = await connector.fetch_all()
        assert isinstance(df, pl.DataFrame)
        assert len(df) == 3
        assert "name" in df.columns

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_fetch_incremental(self, sample_csv_file):
        """Test incremental fetch with key field."""
        connector = FileConnector(sample_csv_file)
        await connector.connect()

        df = await connector.fetch_incremental(last_value=1, key_field="id")
        assert len(df) == 2
        assert df["id"].to_list() == [2, 3]

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_unsupported_file_type(self, tmp_path):
        """Test error on unsupported file type."""
        bad_file = tmp_path / "test.txt"
        bad_file.write_text("some text")

        connector = FileConnector(str(bad_file))
        with pytest.raises(ValueError, match="Unsupported file type"):
            await connector.connect()


class TestPostgreSQLConnector:
    """Tests for PostgreSQLConnector."""

    def test_from_config(self):
        """Test creating connector from config."""
        config = {
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
        }

        connector = PostgreSQLConnector.from_config(config)

        assert connector.host == "localhost"
        assert connector.port == 5432
        assert connector.database == "testdb"
        assert connector.user == "testuser"


class TestConnectorFactory:
    """Tests for ConnectorFactory."""

    def test_create_file_connector(self):
        """Test creating file connector."""
        from app.ingestion.connectors import ConnectorFactory

        config = {"type": "file", "file_path": "/path/to/file.csv"}
        connector = ConnectorFactory.create(config)

        assert isinstance(connector, FileConnector)

    def test_create_postgresql_connector(self):
        """Test creating PostgreSQL connector."""
        from app.ingestion.connectors import ConnectorFactory

        config = {
            "type": "postgresql",
            "host": "localhost",
            "database": "testdb",
            "user": "user",
            "password": "pass",
        }
        connector = ConnectorFactory.create(config)

        assert isinstance(connector, PostgreSQLConnector)

    def test_unknown_connector_type(self):
        """Test error on unknown connector type."""
        from app.ingestion.connectors import ConnectorFactory

        with pytest.raises(ValueError, match="Unknown source type"):
            ConnectorFactory.create({"type": "unknown"})
