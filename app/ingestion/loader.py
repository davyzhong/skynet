"""Data loader for writing DataFrames to database."""

from typing import Literal

import polars as pl
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage.repository import get_session


class DataLoader:
    """Handles loading data into staging tables."""

    @staticmethod
    async def load_to_staging(
        df: pl.DataFrame,
        table_name: str,
        schema: str = "public",
    ) -> int:
        """
        Bulk load DataFrame to staging table.

        Args:
            df: Polars DataFrame to load
            table_name: Target table name
            schema: Database schema

        Returns:
            Number of rows loaded
        """
        if df.is_empty():
            return 0

        full_table_name = f"{schema}.staging_{table_name}"
        columns = df.columns
        columns_sql = ", ".join(columns)
        placeholders = ", ".join([f":{col}" for col in columns])

        insert_sql = text(
            f"""
            INSERT INTO {full_table_name} ({columns_sql})
            VALUES ({placeholders})
            """
        )

        async with get_session() as session:
            for row in df.iter_rows(named=True):
                await session.execute(insert_sql, row)
            await session.commit()

        return len(df)

    @staticmethod
    async def merge_incremental(
        df: pl.DataFrame,
        table_name: str,
        key_columns: list[str],
        schema: str = "public",
    ) -> int:
        """
        Upsert data using key columns for conflict resolution.

        Args:
            df: Polars DataFrame to merge
            table_name: Target table name
            key_columns: Columns to use for conflict detection
            schema: Database schema

        Returns:
            Number of rows merged
        """
        if df.is_empty():
            return 0

        full_table_name = f"{schema}.staging_{table_name}"
        columns = df.columns
        columns_sql = ", ".join(columns)
        placeholders = ", ".join([f":{col}" for col in columns])

        update_set = ", ".join(
            [f"{col} = EXCLUDED.{col}" for col in columns if col not in key_columns]
        )

        upsert_sql = text(
            f"""
            INSERT INTO {full_table_name} ({columns_sql})
            VALUES ({placeholders})
            ON CONFLICT ({", ".join(key_columns)})
            DO UPDATE SET {update_set}
            """
        )

        async with get_session() as session:
            for row in df.iter_rows(named=True):
                await session.execute(upsert_sql, row)
            await session.commit()

        return len(df)

    @staticmethod
    def dataframe_to_dicts(df: pl.DataFrame) -> list[dict]:
        """Convert Polars DataFrame to list of dictionaries."""
        return df.iter_rows(named=True)  # type: ignore
