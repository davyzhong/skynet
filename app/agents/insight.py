"""Insight generation using LLM."""

from datetime import datetime, timedelta
from typing import Any

from app.agents.llm import LLMWrapper
from app.metrics.engine import engine
from app.metrics.registry import registry


class InsightGenerator:
    """Generates insights from metric data using LLM."""

    def __init__(self, llm_wrapper: LLMWrapper | None = None):
        self.llm = llm_wrapper or LLMWrapper()
        self.metrics_engine = engine

    async def generate_daily_insights(self) -> str:
        """
        Generate daily insights summary.

        Returns:
            Natural language insights summary
        """
        now = datetime.utcnow()
        time_range = (now - timedelta(days=1), now)

        metrics_data = await self._collect_metrics_data(time_range)

        if not metrics_data:
            return "No metrics data available for analysis."

        prompt = self._build_insight_prompt(metrics_data)

        try:
            response = await self.llm.complete(prompt, max_tokens=2048)
            return response.content
        except Exception as e:
            return f"Failed to generate insights: {e}"

    async def generate_metric_insights(
        self, metric_name: str, time_range: tuple[datetime, datetime] | None = None
    ) -> str:
        """
        Generate insights for a specific metric.

        Args:
            metric_name: Name of metric
            time_range: Optional time range

        Returns:
            Natural language insights
        """
        if time_range is None:
            now = datetime.utcnow()
            time_range = (now - timedelta(days=7), now)

        df = await self.metrics_engine.compute_metric(metric_name, None, time_range)

        if df is None or df.is_empty():
            return f"No data available for {metric_name}."

        prompt = self._build_single_metric_prompt(metric_name, df)

        try:
            response = await self.llm.complete(prompt, max_tokens=1024)
            return response.content
        except Exception as e:
            return f"Failed to generate insights: {e}"

    async def _collect_metrics_data(
        self, time_range: tuple[datetime, datetime]
    ) -> dict[str, Any]:
        """Collect data for all metrics."""
        metrics_data = {}

        for metric_def in registry.list_all():
            if metric_def.metric_type == "atomic":
                df = await self.metrics_engine.compute_metric(
                    metric_def.name, None, time_range
                )
                if df is not None and not df.is_empty():
                    metrics_data[metric_def.name] = {
                        "current": self._extract_value(df),
                        "description": metric_def.description,
                    }

        return metrics_data

    def _extract_value(self, df) -> float | None:
        """Extract single value from DataFrame."""
        if "value" in df.columns:
            if len(df) == 1:
                return float(df["value"][0])
            return float(df["value"].sum())
        return None

    def _build_insight_prompt(self, metrics_data: dict[str, Any]) -> str:
        """Build prompt for daily insights."""
        metrics_str = "\n".join(
            f"- {name}: {data.get('current', 'N/A')} ({data.get('description', '')})"
            for name, data in metrics_data.items()
        )

        return f"""You are a senior data analyst reviewing SkyNet metrics for the day.

Analyze the following metrics and provide:
1. Key observations
2. Notable trends or anomalies
3. Actionable recommendations

Metrics:
{metrics_str}

Provide a concise, actionable summary in 3-5 bullet points.
Format each point as: • [insight]
"""

    def _build_single_metric_prompt(self, metric_name: str, df) -> str:
        """Build prompt for single metric analysis."""
        data_summary = f"Records: {len(df)}"

        if "value" in df.columns:
            values = df["value"].to_list()
            data_summary += f", Min: {min(values):.2f}, Max: {max(values):.2f}, Avg: {sum(values)/len(values):.2f}"

        return f"""Analyze the following metric and provide insights:

Metric: {metric_name}
Data Summary: {data_summary}

Provide 2-3 key observations about this metric.
"""
