"""Anomaly detection for metrics."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import polars as pl

from app.metrics.engine import engine


class Severity(Enum):
    """Anomaly severity levels."""

    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AnomalyResult:
    """Result of anomaly detection."""

    metric_name: str
    severity: Severity
    current_value: float
    expected_value: float
    deviation: float  # Percentage deviation
    bounds: tuple[float, float]
    message: str


class AnomalyDetector:
    """Statistical anomaly detection for metrics."""

    def __init__(self, std_threshold: float = 2.0, warning_threshold: float = 1.5):
        """
        Initialize detector.

        Args:
            std_threshold: Number of standard deviations for critical anomaly
            warning_threshold: Number of standard deviations for warning
        """
        self.std_threshold = std_threshold
        self.warning_threshold = warning_threshold
        self.metrics_engine = engine

    async def check_metric(
        self,
        metric_name: str,
        dimensions: dict[str, Any] | None = None,
        time_range: tuple[datetime, datetime] | None = None,
    ) -> AnomalyResult | None:
        """
        Check a metric for anomalies.

        Args:
            metric_name: Name of metric to check
            dimensions: Optional dimension filters
            time_range: Optional time range

        Returns:
            AnomalyResult if anomaly detected, None otherwise
        """
        current_df = await self.metrics_engine.compute_metric(
            metric_name, dimensions, time_range
        )

        if current_df is None or current_df.is_empty():
            return None

        if "value" not in current_df.columns:
            return None

        current_value = float(current_df["value"].sum() if len(current_df) > 1 else current_df["value"][0])

        historical_df = await self._get_historical_data(metric_name, dimensions)
        if historical_df is None or len(historical_df) < 3:
            return None

        historical_values = historical_df["value"].to_list()
        mean = sum(historical_values) / len(historical_values)

        variance = sum((x - mean) ** 2 for x in historical_values) / len(historical_values)
        std = variance ** 0.5

        lower_bound = mean - self.std_threshold * std
        upper_bound = mean + self.std_threshold * std

        deviation = ((current_value - mean) / mean * 100) if mean != 0 else 0

        if current_value < lower_bound or current_value > upper_bound:
            severity = Severity.CRITICAL
            message = f"{metric_name} is critically outside normal range"
        elif abs(current_value - mean) > self.warning_threshold * std:
            severity = Severity.WARNING
            message = f"{metric_name} shows unusual variation"
        else:
            severity = Severity.NORMAL
            message = f"{metric_name} is within normal range"

        return AnomalyResult(
            metric_name=metric_name,
            severity=severity,
            current_value=current_value,
            expected_value=mean,
            deviation=deviation,
            bounds=(lower_bound, upper_bound),
            message=message,
        )

    async def check_all_metrics(
        self,
        dimensions: dict[str, Any] | None = None,
    ) -> list[AnomalyResult]:
        """
        Check all registered metrics for anomalies.

        Args:
            dimensions: Optional dimension filters

        Returns:
            List of anomaly results (including normal)
        """
        from app.metrics.registry import registry

        results = []
        now = datetime.utcnow()
        time_range = (now - timedelta(days=7), now)

        for metric_def in registry.list_all():
            if metric_def.metric_type == "atomic":
                result = await self.check_metric(
                    metric_def.name, dimensions, time_range
                )
                if result:
                    results.append(result)

        return results

    async def _get_historical_data(
        self,
        metric_name: str,
        dimensions: dict[str, Any] | None = None,
    ) -> pl.DataFrame | None:
        """Get historical data for a metric."""
        # TODO: Implement actual database query
        # For now, return None to skip historical analysis
        return None


def format_anomaly_message(result: AnomalyResult) -> str:
    """Format anomaly result as notification message."""
    if result.severity == Severity.NORMAL:
        return f"✅ {result.message}"

    emoji = "🔴" if result.severity == Severity.CRITICAL else "🟡"

    return (
        f"{emoji} {result.message}\n"
        f"   Current: {result.current_value:,.2f}\n"
        f"   Expected: {result.expected_value:,.2f}\n"
        f"   Deviation: {result.deviation:+.1f}%\n"
        f"   Bounds: [{result.bounds[0]:,.2f}, {result.bounds[1]:,.2f}]"
    )
