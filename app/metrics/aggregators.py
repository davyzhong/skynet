"""Aggregator functions for metric computations."""

from typing import Any, Callable

import polars as pl


def sum_agg(column: pl.Expr) -> pl.Expr:
    """Sum aggregation."""
    return column.sum()


def count_agg(column: pl.Expr) -> pl.Expr:
    """Count aggregation."""
    return column.count()


def avg_agg(column: pl.Expr) -> pl.Expr:
    """Average aggregation."""
    return column.mean()


def min_agg(column: pl.Expr) -> pl.Expr:
    """Minimum aggregation."""
    return column.min()


def max_agg(column: pl.Expr) -> pl.Expr:
    """Maximum aggregation."""
    return column.max()


def distinct_agg(column: pl.Expr) -> pl.Expr:
    """Count distinct values."""
    return column.n_unique()


def std_agg(column: pl.Expr) -> pl.Expr:
    """Standard deviation."""
    return column.std()


AGGREGATORS: dict[str, Callable[[pl.Expr], pl.Expr]] = {
    "sum": sum_agg,
    "count": count_agg,
    "avg": avg_agg,
    "average": avg_agg,
    "mean": avg_agg,
    "min": min_agg,
    "max": max_agg,
    "distinct": distinct_agg,
    "n_unique": distinct_agg,
    "std": std_agg,
    "stddev": std_agg,
}


def get_aggregator(name: str) -> Callable[[pl.Expr], pl.Expr]:
    """Get aggregator function by name."""
    name_lower = name.lower()
    if name_lower not in AGGREGATORS:
        raise ValueError(f"Unknown aggregator: {name}. Available: {list(AGGREGATORS.keys())}")
    return AGGREGATORS[name_lower]
