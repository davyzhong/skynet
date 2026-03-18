"""Tests for report builder."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.reports.builder import DashboardData, ReportBuilder, ReportConfig


class TestReportBuilder:
    """Tests for ReportBuilder."""

    @pytest.fixture
    def builder(self):
        """Create report builder instance."""
        return ReportBuilder()

    @pytest.fixture
    def sample_config(self):
        """Create sample report config."""
        return ReportConfig(
            name="test_report",
            report_type="summary",
            metric_names=["revenue", "orders"],
            dimensions={"region": "North"},
        )

    def test_format_value(self, builder):
        """Test value formatting."""
        assert builder._format_value(None) == "N/A"
        assert builder._format_value(1500) == "1.5K"
        assert builder._format_value(1500000) == "1.5M"
        assert builder._format_value(0.05) == "5.00%"
        assert builder._format_value(42) == "42.00"

    def test_extract_value_single(self, builder):
        """Test extracting single value from DataFrame."""
        import polars as pl
        df = pl.DataFrame({"value": [100.0]})
        assert builder._extract_value(df) == 100.0

    def test_extract_value_multiple(self, builder):
        """Test extracting sum from multiple rows."""
        import polars as pl
        df = pl.DataFrame({"value": [100.0, 200.0, 300.0]})
        assert builder._extract_value(df) == 600.0

    def test_extract_value_no_value_column(self, builder):
        """Test extracting from DataFrame without value column."""
        import polars as pl
        df = pl.DataFrame({"name": ["a", "b"]})
        assert builder._extract_value(df) is None


class TestDashboardData:
    """Tests for DashboardData dataclass."""

    def test_create_dashboard_data(self):
        """Test creating DashboardData instance."""
        data = DashboardData(
            metric_name="revenue",
            value=1000.0,
            trend=5.5,
            sparkline=[100, 200, 300, 400, 500],
            formatted_value="1.0K",
        )

        assert data.metric_name == "revenue"
        assert data.value == 1000.0
        assert data.trend == 5.5
        assert len(data.sparkline) == 5
