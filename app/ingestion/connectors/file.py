"""File connector for CSV, Excel, and JSON files."""

import os
from typing import Literal

import polars as pl

from app.ingestion.connectors.base import BaseConnector


class FileConnector(BaseConnector):
    """Connector for local file data sources (CSV, Excel, JSON)."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self._file_type: Literal["csv", "excel", "json"] | None = None

    async def connect(self) -> None:
        """Determine file type from extension."""
        ext = os.path.splitext(self.file_path)[1].lower()
        if ext == ".csv":
            self._file_type = "csv"
        elif ext in [".xlsx", ".xls"]:
            self._file_type = "excel"
        elif ext in [".json", ".jsonl"]:
            self._file_type = "json"
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    async def disconnect(self) -> None:
        """No-op for file connector."""
        pass

    async def fetch_all(self, query: str = "") -> pl.DataFrame:
        """Read entire file into DataFrame."""
        if not self._file_type:
            raise RuntimeError("Not connected. Call connect() first.")

        read_options = {}
        if query:
            read_options["schema"] = query

        if self._file_type == "csv":
            return pl.read_csv(self.file_path, **read_options)
        elif self._file_type == "excel":
            return pl.read_excel(self.file_path, **read_options)
        elif self._file_type == "json":
            return pl.read_json(self.file_path, **read_options)
        else:
            raise RuntimeError(f"Unknown file type: {self._file_type}")

    async def fetch_incremental(
        self, query: str = "", last_value: int = 0, key_field: str = "id"
    ) -> pl.DataFrame:
        """Read file and filter by key field."""
        df = await self.fetch_all(query)
        if key_field in df.columns:
            return df.filter(pl.col(key_field) > last_value)
        return df

    @classmethod
    def from_config(cls, config: dict) -> "FileConnector":
        """Create connector from configuration dictionary."""
        return cls(file_path=config["file_path"])
