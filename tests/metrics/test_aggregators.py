"""Tests for aggregator functions."""

import pytest
import polars as pl

from app.metrics.aggregators import (
    AGGREGATORS,
    avg_agg,
    count_agg,
    get_aggregator,
    max_agg,
    min_agg,
    sum_agg,
    std_agg,
)


class TestAggregators:
    """Tests for aggregator functions."""

    @pytest.fixture
    def sample_df(self):
        """Create sample DataFrame for testing."""
        return pl.DataFrame({
            "category": ["A", "A", "B", "B", "C"],
            "value": [10.0, 20.0, 30.0, 40.0, 50.0],
        })

    def test_sum_agg(self, sample_df):
        """Test sum aggregation."""
        result = sample_df.select(sum_agg(pl.col("value")))
        assert result.item() == 150.0

    def test_count_agg(self, sample_df):
        """Test count aggregation."""
        result = sample_df.select(count_agg(pl.col("value")))
        assert result.item() == 5

    def test_avg_agg(self, sample_df):
        """Test average aggregation."""
        result = sample_df.select(avg_agg(pl.col("value")))
        assert result.item() == 30.0

    def test_min_agg(self, sample_df):
        """Test min aggregation."""
        result = sample_df.select(min_agg(pl.col("value")))
        assert result.item() == 10.0

    def test_max_agg(self, sample_df):
        """Test max aggregation."""
        result = sample_df.select(max_agg(pl.col("value")))
        assert result.item() == 50.0

    def test_std_agg(self, sample_df):
        """Test standard deviation aggregation."""
        result = sample_df.select(std_agg(pl.col("value")))
        assert result is not None

    def test_get_aggregator(self):
        """Test getting aggregator by name."""
        assert get_aggregator("sum") == sum_agg
        assert get_aggregator("count") == count_agg
        assert get_aggregator("avg") == avg_agg
        assert get_aggregator("AVG") == avg_agg  # Case insensitive

    def test_get_aggregator_unknown(self):
        """Test error on unknown aggregator."""
        with pytest.raises(ValueError, match="Unknown aggregator"):
            get_aggregator("unknown")

    def test_aggregators_dict(self):
        """Test that AGGREGATORS dict has expected keys."""
        expected = ["sum", "count", "avg", "min", "max", "distinct", "std"]
        for key in expected:
            assert key in AGGREGATORS
