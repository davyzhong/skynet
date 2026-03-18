"""Metric definition registry loaded from configuration."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class WindowConfig:
    """Configuration for time-window metrics."""

    window_type: str = "rolling"  # rolling, sliding, cumulative
    window_size: int = 7  # days
    window_unit: str = "day"


@dataclass
class MetricDefinition:
    """Definition of a metric."""

    name: str
    metric_type: str  # atomic, derived, window
    source_table: str | None = None
    field: str | None = None
    aggregation: str | None = None
    dimensions: list[str] = field(default_factory=list)
    filters: dict[str, Any] = field(default_factory=dict)
    window_config: WindowConfig | None = None
    description: str | None = None
    formula: str | None = None  # For derived metrics

    @classmethod
    def from_dict(cls, data: dict) -> "MetricDefinition":
        """Create MetricDefinition from dictionary."""
        if "window_config" in data and data["window_config"]:
            data["window_config"] = WindowConfig(**data["window_config"])

        return cls(**data)


class MetricRegistry:
    """Registry for metric definitions."""

    def __init__(self):
        self._metrics: dict[str, MetricDefinition] = {}

    def load_from_yaml(self, path: str | Path) -> None:
        """Load metrics from YAML configuration file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Metrics config not found: {path}")

        with open(path) as f:
            config = yaml.safe_load(f)

        metrics_list = config.get("metrics", [])
        for metric_data in metrics_list:
            metric = MetricDefinition.from_dict(metric_data)
            self._metrics[metric.name] = metric

    def load_from_dict(self, metrics_data: list[dict]) -> None:
        """Load metrics from dictionary configuration."""
        for metric_data in metrics_data:
            metric = MetricDefinition.from_dict(metric_data)
            self._metrics[metric.name] = metric

    def get(self, name: str) -> MetricDefinition | None:
        """Get metric definition by name."""
        return self._metrics.get(name)

    def list_all(self) -> list[MetricDefinition]:
        """List all registered metric definitions."""
        return list(self._metrics.values())

    def register(self, metric: MetricDefinition) -> None:
        """Register a new metric definition."""
        self._metrics[metric.name] = metric

    def unregister(self, name: str) -> bool:
        """Unregister a metric definition."""
        if name in self._metrics:
            del self._metrics[name]
            return True
        return False


# Global registry instance
registry = MetricRegistry()
