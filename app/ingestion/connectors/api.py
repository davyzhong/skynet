"""REST API connector with pagination and authentication."""

from typing import Any

import httpx
import polars as pl
from pydantic import BaseModel

from app.ingestion.connectors.base import BaseConnector


class APIConnectorConfig(BaseModel):
    """Configuration for API connector."""

    base_url: str
    auth_type: str = "none"  # none, bearer, api_key, token
    auth_value: str | None = None
    headers: dict[str, str] = {}
    pagination_type: str = "none"  # none, cursor, offset, page
    page_param: str = "page"
    offset_param: str = "offset"
    cursor_param: str = "cursor"
    limit_param: str = "limit"
    default_limit: int = 1000


class APIConnector(BaseConnector):
    """Connector for REST API data sources."""

    def __init__(self, config: APIConnectorConfig):
        self.config = config
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        """Initialize HTTP client with authentication."""
        headers = dict(self.config.headers)

        if self.config.auth_type == "bearer" and self.config.auth_value:
            headers["Authorization"] = f"Bearer {self.config.auth_value}"
        elif self.config.auth_type == "api_key" and self.config.auth_value:
            headers["X-API-Key"] = self.config.auth_value
        elif self.config.auth_type == "token" and self.config.auth_value:
            headers["Authorization"] = f"Token {self.config.auth_value}"

        self._client = httpx.AsyncClient(
            base_url=self.config.base_url,
            headers=headers,
            timeout=30.0,
        )

    async def disconnect(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _fetch_page(
        self, endpoint: str, params: dict[str, Any]
    ) -> tuple[list[dict], int | None]:
        """Fetch a single page of data."""
        if not self._client:
            raise RuntimeError("Not connected. Call connect() first.")

        response = await self._client.get(endpoint, params=params)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, dict) and "data" in data:
            items = data["data"]
            next_cursor = data.get("next_cursor") or data.get("next_page")
        elif isinstance(data, list):
            items = data
            next_cursor = None
        else:
            items = data if isinstance(data, list) else [data]
            next_cursor = None

        return items, next_cursor

    async def fetch_all(self, query: str = "") -> pl.DataFrame:
        """Fetch all data with pagination."""
        if not self._client:
            raise RuntimeError("Not connected. Call connect() first.")

        all_items: list[dict] = []
        params = {self.config.limit_param: self.config.default_limit}
        cursor: int | str | None = None

        endpoint = query if query else "/"

        while True:
            if self.config.pagination_type == "offset":
                params[self.config.offset_param] = cursor if cursor else 0
            elif self.config.pagination_type == "page":
                params[self.config.page_param] = cursor if cursor else 1
            elif self.config.pagination_type == "cursor" and cursor:
                params[self.config.cursor_param] = cursor

            items, next_cursor = await self._fetch_page(endpoint, params)

            if not items:
                break

            all_items.extend(items if isinstance(items, list) else [items])

            cursor = next_cursor
            if cursor is None:
                break

        if not all_items:
            return pl.DataFrame()

        return pl.DataFrame(all_items)

    async def fetch_incremental(
        self, query: str = "", last_value: Any = None, key_field: str = "id"
    ) -> pl.DataFrame:
        """Fetch incremental data."""
        if not self._client:
            raise RuntimeError("Not connected. Call connect() first.")

        all_items: list[dict] = []
        params = {self.config.limit_param: self.config.default_limit}

        endpoint = query if query else "/"

        while True:
            items, next_cursor = await self._fetch_page(endpoint, params)

            if not items:
                break

            filtered_items = [
                item
                for item in (items if isinstance(items, list) else [items])
                if item.get(key_field, 0) > (last_value or 0)
            ]
            all_items.extend(filtered_items)

            if next_cursor is None:
                break

            params[self.config.cursor_param] = next_cursor

        if not all_items:
            return pl.DataFrame()

        return pl.DataFrame(all_items)

    @classmethod
    def from_config(cls, config: dict) -> "APIConnector":
        """Create connector from configuration dictionary."""
        api_config = APIConnectorConfig(**config)
        return cls(config=api_config)
