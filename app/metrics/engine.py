"""Metrics computation engine."""

from datetime import datetime, timedelta
from typing import Any

import polars as pl

from app.metrics.aggregators import get_aggregator
from app.metrics.registry import MetricDefinition, registry
from app.storage.models import MetricValue
from app.storage.repository import MetricRepository, MetricValueRepository, get_session


class MetricsEngine:
    """Engine for computing metrics from raw data."""

    def __init__(self):
        self.registry = registry

    async def compute_metric(
        self,
        name: str,
        dimensions: dict[str, Any] | None = None,
        time_range: tuple[datetime, datetime] | None = None,
    ) -> pl.DataFrame | None:
        """
        Compute a metric by name.

        Args:
            name: Metric name
            dimensions: Dimension filters
            time_range: Optional time range (start, end)

        Returns:
            DataFrame with computed metric values
        """
        metric_def = self.registry.get(name)
        if not metric_def:
            return None

        if metric_def.metric_type == "atomic":
            return await self._compute_atomic(metric_def, dimensions, time_range)
        elif metric_def.metric_type == "derived":
            return await self._compute_derived(metric_def, dimensions, time_range)
        elif metric_def.metric_type == "window":
            return await self._compute_window(metric_def, dimensions, time_range)
        else:
            raise ValueError(f"Unknown metric type: {metric_def.metric_type}")

    async def _compute_atomic(
        self,
        metric_def: MetricDefinition,
        dimensions: dict[str, Any] | None,
        time_range: tuple[datetime, datetime] | None,
    ) -> pl.DataFrame | None:
        """Compute atomic metric (simple aggregation)."""
        if not metric_def.source_table or not metric_def.field:
            return None

        df = await self._fetch_source_data(metric_def.source_table, time_range)
        if df.is_empty():
            return pl.DataFrame()

        if metric_def.filters:
            df = self._apply_filters(df, metric_def.filters)

        if not metric_def.dimensions:
            agg_expr = get_aggregator(metric_def.aggregation or "sum")(
                pl.col(metric_def.field)
            )
            result = df.select(agg_expr.alias("value"))
            return result

        group_by = [pl.col(d) for d in metric_def.dimensions]
        agg_expr = get_aggregator(metric_def.aggregation or "sum")(
            pl.col(metric_def.field)
        ).alias("value")

        result = df.group_by(metric_def.dimensions).agg(agg_expr)

        if dimensions:
            for dim, val in dimensions.items():
                result = result.filter(pl.col(dim) == val)

        return result

    async def _compute_derived(
        self,
        metric_def: MetricDefinition,
        dimensions: dict[str, Any] | None,
        time_range: tuple[datetime, datetime] | None,
    ) -> pl.DataFrame | None:
        """Compute derived metric (composition of other metrics)."""
        if not metric_def.formula:
            return None

        formula_parts = metric_def.formula.split("/")
        if len(formula_parts) != 2:
            raise ValueError(f"Invalid derived formula: {metric_def.formula}")

        numerator_name = formula_parts[0].strip()
        denominator_name = formula_parts[1].strip()

        numerator_df = await self.compute_metric(numerator_name, dimensions, time_range)
        denominator_df = await self.compute_metric(denominator_name, dimensions, time_range)

        if numerator_df is None or denominator_df is None:
            return None

        if numerator_df.is_empty() or denominator_df.is_empty():
            return pl.DataFrame({"value": []})

        joined = numerator_df.join(denominator_df, on=numerator_df.columns[:-1], how="left")
        result = joined.with_columns(
            (pl.col("value") / pl.col("value_right")).alias("value")
        ).select(pl.all().exclude("value_right"))

        return result

    async def _compute_window(
        self,
        metric_def: MetricDefinition,
        dimensions: dict[str, Any] | None,
        time_range: tuple[datetime, datetime] | None,
    ) -> pl.DataFrame | None:
        """Compute window metric (time-window calculations)."""
        if not metric_def.source_table or not metric_def.field:
            return None

        if not metric_def.window_config:
            return None

        df = await self._fetch_source_data(metric_def.source_table, time_range)
        if df.is_empty():
            return pl.DataFrame()

        window_size = metric_def.window_config.window_size
        window_unit = metric_def.window_config.window_unit

        if "date" not in df.columns and "created_at" not in df.columns:
            return None

        date_col = "date" if "date" in df.columns else "created_at"

        if window_unit == "day":
            window_expr = pl.col(date_col).cast(pl.Date).offset_by(f"-{window_size}d")
        else:
            window_expr = pl.col(date_col).offset_by(f"-{window_size}{window_unit[0]}")

        if metric_def.dimensions:
            group_by = metric_def.dimensions + [date_col]
            agg_expr = get_aggregator(metric_def.aggregation or "sum")(
                pl.col(metric_def.field)
            ).alias("value")

            result = (
                df.sort(date_col)
                .group_by(metric_def.dimensions)
                .agg([pl.col(metric_def.field).sum().alias("value"), date_col])
            )

            for dim in metric_def.dimensions:
                result = result.with_columns(
                    pl.col("value")
                    .shift_and_fill(1, pl.col("value"))
                    .over(dim)
                )

            result = result.with_columns(
                ((pl.col("value") - pl.col("value").shift(1)) / pl.col("value").shift(1) * 100).alias("change_pct")
            )

            return result

        return pl.DataFrame()

    async def compute_all_scheduled(self) -> list[dict]:
        """Compute all metrics that are scheduled for computation."""
        results = []
        for metric_def in self.registry.list_all():
            if metric_def.metric_type == "atomic":
                result = await self.compute_metric(metric_def.name)
                if result is not None:
                    await self._save_metric_value(metric_def.name, result)
                    results.append({"metric": metric_def.name, "status": "success"})
            elif metric_def.metric_type == "window":
                result = await self.compute_metric(metric_def.name)
                if result is not None:
                    await self._save_metric_value(metric_def.name, result)
                    results.append({"metric": metric_def.name, "status": "success"})
        return results

    async def _fetch_source_data(
        self, table_name: str, time_range: tuple[datetime, datetime] | None
    ) -> pl.DataFrame:
        """Fetch data from source table."""
        # TODO: Implement actual database query
        # For now, return empty DataFrame
        return pl.DataFrame()

    def _apply_filters(
        self, df: pl.DataFrame, filters: dict[str, Any]
    ) -> pl.DataFrame:
        """Apply filters to DataFrame."""
        for column, value in filters.items():
            if column in df.columns:
                if isinstance(value, dict):
                    if "gt" in value:
                        df = df.filter(pl.col(column) > value["gt"])
                    if "gte" in value:
                        df = df.filter(pl.col(column) >= value["gte"])
                    if "lt" in value:
                        df = df.filter(pl.col(column) < value["lt"])
                    if "lte" in value:
                        df = df.filter(pl.col(column) <= value["lte"])
                    if "in" in value:
                        df = df.filter(pl.col(column).is_in(value["in"]))
                else:
                    df = df.filter(pl.col(column) == value)
        return df

    async def _save_metric_value(
        self, metric_name: str, result: pl.DataFrame
    ) -> None:
        """Save computed metric value to database."""
        async with get_session() as session:
            metric_repo = MetricRepository(session)
            metric_value_repo = MetricValueRepository(session)

            metric = await metric_repo.find_by_id(1)  # TODO: Look up by name
            if metric is None:
                return

            now = datetime.utcnow()

            if "value" in result.columns:
                for row in result.iter_rows(named=True):
                    dimensions = {k: v for k, v in row.items() if k != "value"}
                    await metric_value_repo.create(
                        metric_id=metric.id,
                        value=float(row["value"]),
                        dimensions=dimensions if dimensions else None,
                        computed_at=now,
                    )


# Global engine instance
engine = MetricsEngine()
