"""Tests for report renderers."""

import pytest
from datetime import datetime

from app.reports.renderer import (
    ExcelRenderer,
    ImageRenderer,
    MarkdownRenderer,
)


class TestMarkdownRenderer:
    """Tests for MarkdownRenderer."""

    @pytest.fixture
    def renderer(self):
        """Create Markdown renderer instance."""
        return MarkdownRenderer()

    @pytest.fixture
    def sample_report(self):
        """Create sample report data."""
        return {
            "report_name": "Test Report",
            "report_type": "summary",
            "generated_at": "2024-01-01T00:00:00",
            "metrics": {
                "revenue": {"value": 1000.0},
                "orders": {"value": 50},
            },
        }

    def test_render_summary_report(self, renderer, sample_report):
        """Test rendering a summary report."""
        result = renderer.render(sample_report)

        assert "# Test Report" in result
        assert "Test Report" in result
        assert "| revenue | 1000.00 |" in result
        assert "| orders | 50 |" in result

    def test_render_dashboard_report(self, renderer):
        """Test rendering a dashboard report."""
        report = {
            "report_name": "Dashboard",
            "report_type": "dashboard",
            "generated_at": "2024-01-01T00:00:00",
            "dashboard": {
                "revenue": {
                    "value": 1000.0,
                    "trend": 5.5,
                    "sparkline": [100, 200, 300],
                    "formatted_value": "1.0K",
                },
            },
        }

        result = renderer.render(report)

        assert "# Dashboard" in result
        assert "revenue" in result
        assert "1.0K" in result
        assert "+5.5%" in result

    def test_render_empty_metrics(self, renderer):
        """Test rendering report with no metrics."""
        report = {
            "report_name": "Empty",
            "report_type": "summary",
            "metrics": {},
        }

        result = renderer.render(report)
        assert "# Empty" in result


class TestExcelRenderer:
    """Tests for ExcelRenderer."""

    @pytest.fixture
    def renderer(self):
        """Create Excel renderer instance."""
        return ExcelRenderer()

    @pytest.fixture
    def sample_report(self):
        """Create sample report data."""
        return {
            "report_name": "Test",
            "report_type": "summary",
            "generated_at": "2024-01-01T00:00:00",
            "metrics": {
                "revenue": {"value": 1000.0},
            },
        }

    def test_render_excel(self, renderer, sample_report):
        """Test rendering Excel file."""
        result = renderer.render(sample_report)

        assert isinstance(result, bytes)
        assert len(result) > 0

        # Verify it's a valid ZIP (xlsx is a ZIP archive)
        assert result[:2] == b"PK"

    def test_render_dashboard_excel(self, renderer):
        """Test rendering dashboard report to Excel."""
        report = {
            "report_name": "Dashboard",
            "report_type": "dashboard",
            "generated_at": "2024-01-01T00:00:00",
            "dashboard": {
                "revenue": {
                    "value": 1000.0,
                    "trend": 5.5,
                    "formatted_value": "1.0K",
                },
            },
        }

        result = renderer.render(report)

        assert isinstance(result, bytes)
        assert result[:2] == b"PK"


class TestImageRenderer:
    """Tests for ImageRenderer."""

    @pytest.fixture
    def renderer(self):
        """Create Image renderer instance."""
        return ImageRenderer()

    def test_render_empty_dashboard(self, renderer):
        """Test rendering empty dashboard."""
        report = {
            "report_name": "Empty",
            "report_type": "dashboard",
            "dashboard": {},
        }

        # Should not raise, returns empty PNG
        result = renderer.render(report)
        assert isinstance(result, bytes)

    def test_get_color(self, renderer):
        """Test color selection."""
        assert renderer._get_color(1) == "#4472C4"
        assert renderer._get_color(2) == "#ED7D31"
        assert renderer._get_color(6) == "#4472C4"  # Cycles
