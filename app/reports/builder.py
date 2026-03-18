"""Report builder for generating reports from metrics."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import polars as pl

from app.metrics.engine import engine


@dataclass
class ReportConfig:
    """Configuration for report generation."""

    name: str
    report_type: str  # summary, detailed, dashboard
    metric_names: list[str]
    dimensions: dict[str, Any] | None = None
    time_range: tuple[datetime, datetime] | None = None
    format_options: dict[str, Any] | None = None


@dataclass
class DashboardData:
    """Dashboard data for a metric."""

    metric_name: str
    value: float | None
    trend: float | None  # Percentage change
    sparkline: list[float] | None
    formatted_value: str | None = None


class ReportBuilder:
    """Builder for generating reports from metrics."""

    def __init__(self):
        self.metrics_engine = engine

    async def build(self, config: ReportConfig) -> dict[str, Any]:
        """
        Build a report based on configuration.

        Args:
            config: Report configuration

        Returns:
            Dictionary containing report data
        """
        if config.report_type == "summary":
            return await self._build_summary(config)
        elif config.report_type == "detailed":
            return await self._build_detailed(config)
        elif config.report_type == "dashboard":
            return await self._build_dashboard(config)
        else:
            raise ValueError(f"Unknown report type: {config.report_type}")

    async def _build_summary(self, config: ReportConfig) -> dict[str, Any]:
        """Build summary report."""
        results = {}
        for metric_name in config.metric_names:
            df = await self.metrics_engine.compute_metric(
                metric_name, config.dimensions, config.time_range
            )
            if df is not None and not df.is_empty():
                if "value" in df.columns:
                    results[metric_name] = {
                        "value": float(df["value"].sum()) if len(df) > 1 else float(df["value"][0]),
                        "rows": len(df),
                    }
                else:
                    results[metric_name] = {"data": df.to_dicts()}
            else:
                results[metric_name] = {"value": None}

        return {
            "report_name": config.name,
            "report_type": "summary",
            "generated_at": datetime.utcnow().isoformat(),
            "metrics": results,
        }

    async def _build_detailed(self, config: ReportConfig) -> dict[str, Any]:
        """Build detailed report with all dimensions."""
        results = {}
        for metric_name in config.metric_names:
            df = await self.metrics_engine.compute_metric(
                metric_name, None, config.time_range
            )
            if df is not None and not df.is_empty():
                results[metric_name] = {
                    "data": df.to_dicts(),
                    "total_rows": len(df),
                }
            else:
                results[metric_name] = {"data": [], "total_rows": 0}

        return {
            "report_name": config.name,
            "report_type": "detailed",
            "generated_at": datetime.utcnow().isoformat(),
            "metrics": results,
        }

    async def _build_dashboard(self, config: ReportConfig) -> dict[str, Any]:
        """Build dashboard data with trends and sparklines."""
        dashboard_data = {}

        for metric_name in config.metric_names:
            current_df = await self.metrics_engine.compute_metric(
                metric_name, config.dimensions, config.time_range
            )

            if current_df is not None and not current_df.is_empty():
                current_value = self._extract_value(current_df)
                trend = await self._calculate_trend(metric_name, config.dimensions)
                sparkline = await self._generate_sparkline(
                    metric_name, config.dimensions
                )

                dashboard_data[metric_name] = DashboardData(
                    metric_name=metric_name,
                    value=current_value,
                    trend=trend,
                    sparkline=sparkline,
                    formatted_value=self._format_value(current_value),
                )
            else:
                dashboard_data[metric_name] = DashboardData(
                    metric_name=metric_name,
                    value=None,
                    trend=None,
                    sparkline=None,
                    formatted_value="N/A",
                )

        return {
            "report_name": config.name,
            "report_type": "dashboard",
            "generated_at": datetime.utcnow().isoformat(),
            "dashboard": {
                name: {
                    "value": data.value,
                    "trend": data.trend,
                    "sparkline": data.sparkline,
                    "formatted_value": data.formatted_value,
                }
                for name, data in dashboard_data.items()
            },
        }

    def _extract_value(self, df: pl.DataFrame) -> float | None:
        """Extract single value from DataFrame."""
        if "value" in df.columns:
            if len(df) == 1:
                return float(df["value"][0])
            return float(df["value"].sum())
        return None

    async def _calculate_trend(
        self, metric_name: str, dimensions: dict[str, Any] | None
    ) -> float | None:
        """Calculate trend percentage compared to previous period."""
        now = datetime.utcnow()
        current_range = (now.replace(day=1), now)
        previous_end = current_range[0]
        previous_start = previous_end.replace(day=1)
        previous_range = (previous_start, previous_end)

        current_df = await self.metrics_engine.compute_metric(
            metric_name, dimensions, current_range
        )
        previous_df = await self.metrics_engine.compute_metric(
            metric_name, dimensions, previous_range
        )

        if current_df is None or previous_df is None:
            return None

        current_value = self._extract_value(current_df)
        previous_value = self._extract_value(previous_df)

        if current_value is None or previous_value is None or previous_value == 0:
            return None

        return ((current_value - previous_value) / previous_value) * 100

    async def _generate_sparkline(
        self, metric_name: str, dimensions: dict[str, Any] | None, points: int = 7
    ) -> list[float] | None:
        """Generate sparkline data points."""
        now = datetime.utcnow()
        sparkline_data = []

        for i in range(points):
            end = now.replace(hour=0, minute=0, second=0, microsecond=0)
            start = end.replace(hour=0) - (i * 24 * 3600)
            time_range = (start, end)

            df = await self.metrics_engine.compute_metric(metric_name, dimensions, time_range)
            if df is not None and not df.is_empty():
                value = self._extract_value(df)
                if value is not None:
                    sparkline_data.append(value)

        return sparkline_data if sparkline_data else None

    def _format_value(self, value: float | None) -> str:
        """Format value for display."""
        if value is None:
            return "N/A"

        if abs(value) >= 1_000_000:
            return f"{value / 1_000_000:.1f}M"
        elif abs(value) >= 1_000:
            return f"{value / 1_000:.1f}K"
        elif abs(value) < 1:
            return f"{value:.2%}"
        else:
            return f"{value:.2f}"
