"""Tests for sync manager."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.ingestion.sync import SyncManager
from app.storage.models import DataSource, JobStatus, SyncMode


class TestSyncManager:
    """Tests for SyncManager."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def mock_data_source(self):
        """Create a mock data source."""
        return MagicMock(spec=DataSource)

    @pytest.mark.asyncio
    async def test_run_sync_source_not_found(self):
        """Test error when data source not found."""
        manager = SyncManager()

        with patch("app.ingestion.sync.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch.object(
                manager, "_get_data_source", new_callable=AsyncMock, return_value=None
            ):
                result = await manager.run_sync("nonexistent")

        assert result["status"] == "error"
        assert "not found" in result["message"]

    @pytest.mark.asyncio
    async def test_get_last_sync_value(self, mock_session):
        """Test retrieving last sync value."""
        manager = SyncManager()

        mock_jobs = [
            MagicMock(
                data_source_id=1,
                status=JobStatus.COMPLETED,
                sync_mode=SyncMode.INCREMENTAL,
                rows_synced=100,
                completed_at=None,
                created_at=None,
            )
        ]

        with patch("app.ingestion.sync.SyncJobRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.find_all = AsyncMock(return_value=mock_jobs)
            mock_repo_class.return_value = mock_repo

            value = await manager._get_last_sync_value(mock_session, 1)
            # Note: This test may need adjustment based on actual implementation
