"""Sync manager for orchestrating data synchronization."""

from datetime import datetime
from typing import Any

from app.config import get_settings
from app.ingestion.connectors import ConnectorFactory
from app.storage.models import DataSource, JobStatus, SyncJob, SyncMode
from app.storage.repository import DataSourceRepository, SyncJobRepository, get_session


class SyncManager:
    """Manages data synchronization from various sources."""

    def __init__(self):
        self.settings = get_settings()

    async def run_sync(
        self,
        source_name: str,
        force_full: bool = False,
        query: str | None = None,
    ) -> dict[str, Any]:
        """
        Run synchronization for a data source.

        Args:
            source_name: Name of the data source to sync
            force_full: If True, perform full sync instead of incremental
            query: Optional SQL query or endpoint path

        Returns:
            Dictionary with sync results
        """
        async with get_session() as session:
            data_source_repo = DataSourceRepository(session)
            sync_job_repo = SyncJobRepository(session)

            data_source = await data_source_repo.find_by_id(int(source_name))
            if not data_source:
                return {"status": "error", "message": f"Data source not found: {source_name}"}

            sync_job = await sync_job_repo.create(
                data_source_id=data_source.id,
                status=JobStatus.RUNNING,
                sync_mode=SyncMode.FULL if force_full else SyncMode.INCREMENTAL,
            )

            try:
                connector = ConnectorFactory.create(data_source.config)

                async with connector:
                    if force_full:
                        df = await connector.fetch_all(query or "")
                    else:
                        last_value = await self._get_last_sync_value(session, data_source.id)
                        df = await connector.fetch_incremental(
                            query or "", last_value or 0
                        )

                    if not df.is_empty():
                        await self._load_to_staging(session, df, data_source.name)

                    sync_job.rows_synced = len(df)
                    sync_job.status = JobStatus.COMPLETED
                    sync_job.completed_at = datetime.utcnow()

                    await session.commit()

                    return {
                        "status": "success",
                        "job_id": sync_job.id,
                        "rows_synced": len(df),
                    }

            except Exception as e:
                sync_job.status = JobStatus.FAILED
                sync_job.error_message = str(e)
                sync_job.completed_at = datetime.utcnow()
                await session.commit()

                return {
                    "status": "error",
                    "job_id": sync_job.id,
                    "message": str(e),
                }

    async def _get_last_sync_value(
        self, session, data_source_id: int
    ) -> int | None:
        """Get the last sync value for incremental sync."""
        sync_job_repo = SyncJobRepository(session)
        jobs = await sync_job_repo.find_all()

        completed_jobs = [
            j for j in jobs if j.data_source_id == data_source_id
            and j.status == JobStatus.COMPLETED
            and j.sync_mode == SyncMode.INCREMENTAL
        ]

        if completed_jobs:
            last_job = max(completed_jobs, key=lambda j: j.completed_at or j.created_at)
            return last_job.rows_synced

        return None

    async def _load_to_staging(
        self, session, df, table_name: str
    ) -> None:
        """Load DataFrame to staging table."""
        from sqlalchemy import text

        columns = df.columns
        placeholders = [f":{col}" for col in columns]
        columns_sql = ", ".join(columns)
        placeholders_sql = ", ".join(placeholders)

        insert_sql = text(
            f"""
            INSERT INTO staging_{table_name} ({columns_sql})
            VALUES ({placeholders_sql})
            ON CONFLICT DO NOTHING
            """
        )

        for row in df.iter_rows(named=True):
            await session.execute(insert_sql, row)
