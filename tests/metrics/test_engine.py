"""Tests for metrics engine."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl

from app.metrics.engine import MetricsEngine
from app.metrics.registry import MetricDefinition, MetricRegistry, WindowConfig


class TestMetricsEngine:
    """Tests for MetricsEngine."""

    @pytest.fixture
    def engine(self):
        """Create metrics engine instance."""
        return MetricsEngine()

    @pytest.fixture
    def sample_metric_def(self):
        """Create sample atomic metric definition."""
        return MetricDefinition(
            name="total_revenue",
            metric_type="atomic",
            source_table="orders",
            field="amount",
            aggregation="sum",
            dimensions=["region"],
            filters={},
        )

    @pytest.fixture
    def sample_derived_def(self):
        """Create sample derived metric definition."""
        return MetricDefinition(
            name="average_order_value",
            metric_type="derived",
            formula="total_revenue / order_count",
        )

    @pytest.fixture
    def sample_df(self):
        """Create sample DataFrame."""
        return pl.DataFrame({
            "region": ["North", "South", "North", "South"],
            "amount": [100.0, 200.0, 150.0, 250.0],
        })

    def test_apply_filters(self, engine, sample_df):
        """Test applying filters to DataFrame."""
        filters = {"region": "North"}
        result = engine._apply_filters(sample_df, filters)

        assert len(result) == 2
        assert all(result["region"] == "North")

    def test_apply_filters_numeric(self, engine, sample_df):
        """Test applying numeric filters."""
        filters = {"amount": {"gt": 150.0}}
        result = engine._apply_filters(sample_df, filters)

        assert len(result) == 2
        assert all(result["amount"] > 150.0)


class TestMetricRegistry:
    """Tests for MetricRegistry."""

    @pytest.fixture
    def registry(self):
        """Create fresh registry."""
        return MetricRegistry()

    def test_register_and_get(self, registry):
        """Test registering and retrieving a metric."""
        metric = MetricDefinition(
            name="test_metric",
            metric_type="atomic",
        )
        registry.register(metric)

        retrieved = registry.get("test_metric")
        assert retrieved is not None
        assert retrieved.name == "test_metric"

    def test_get_nonexistent(self, registry):
        """Test getting nonexistent metric returns None."""
        assert registry.get("nonexistent") is None

    def test_list_all(self, registry):
        """Test listing all metrics."""
        metric1 = MetricDefinition(name="metric1", metric_type="atomic")
        metric2 = MetricDefinition(name="metric2", metric_type="derived")

        registry.register(metric1)
        registry.register(metric2)

        all_metrics = registry.list_all()
        assert len(all_metrics) == 2

    def test_unregister(self, registry):
        """Test unregistering a metric."""
        metric = MetricDefinition(name="to_remove", metric_type="atomic")
        registry.register(metric)

        assert registry.unregister("to_remove") is True
        assert registry.get("to_remove") is None

    def test_unregister_nonexistent(self, registry):
        """Test unregistering nonexistent metric returns False."""
        assert registry.unregister("nonexistent") is False

    def test_load_from_dict(self, registry):
        """Test loading metrics from dictionary."""
        metrics_data = [
            {
                "name": "revenue",
                "metric_type": "atomic",
                "source_table": "orders",
                "field": "amount",
                "aggregation": "sum",
            },
            {
                "name": "order_count",
                "metric_type": "atomic",
                "source_table": "orders",
                "field": "id",
                "aggregation": "count",
            },
        ]

        registry.load_from_dict(metrics_data)

        assert registry.get("revenue") is not None
        assert registry.get("order_count") is not None

    def test_window_config_from_dict(self):
        """Test creating WindowConfig from dictionary."""
        data = {
            "name": "rolling_avg",
            "metric_type": "window",
            "window_config": {
                "window_type": "rolling",
                "window_size": 7,
                "window_unit": "day",
            },
        }

        metric = MetricDefinition.from_dict(data)

        assert metric.window_config is not None
        assert metric.window_config.window_size == 7
        assert metric.window_config.window_unit == "day"
