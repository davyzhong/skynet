"""Natural language query processing."""

from typing import Any

from app.agents.llm import LLMWrapper
from app.metrics.registry import registry


class NLQueryProcessor:
    """Processes natural language queries to metric queries."""

    def __init__(self, llm_wrapper: LLMWrapper | None = None):
        self.llm = llm_wrapper or LLMWrapper()

    async def process(self, query: str) -> dict[str, Any]:
        """
        Process natural language query.

        Args:
            query: Natural language query from user

        Returns:
            Dictionary with parsed intent and response
        """
        schema = self._build_schema_prompt()

        prompt = f"""You are a data analyst assistant for SkyNet, an enterprise data intelligence platform.

Given the user's question, extract the metric name, dimensions, and time range.

Available metrics:
{schema}

User question: {query}

Respond in JSON format:
{{
  "metric_name": "extracted metric name",
  "dimensions": {{"dimension": "value"}},
  "time_range": "today/yesterday/this_week/this_month/last_7_days/last_30_days",
  "confidence": 0.0-1.0
}}
"""

        try:
            response = await self.llm.complete(prompt)
            result = self._parse_response(response.content)
            return result
        except Exception as e:
            return {
                "error": str(e),
                "metric_name": None,
                "dimensions": {},
                "time_range": None,
                "confidence": 0.0,
            }

    def _build_schema_prompt(self) -> str:
        """Build schema description for prompt."""
        metrics = registry.list_all()
        if not metrics:
            return "No metrics defined yet."

        lines = []
        for metric in metrics:
            lines.append(f"- {metric.name}: {metric.description or metric.metric_type}")
            if metric.dimensions:
                lines.append(f"  Dimensions: {', '.join(metric.dimensions)}")

        return "\n".join(lines)

    def _parse_response(self, content: str) -> dict[str, Any]:
        """Parse LLM response to extract query details."""
        import json
        import re

        json_match = re.search(r"\{[^{}]*\}", content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        return {
            "error": "Failed to parse response",
            "metric_name": None,
            "dimensions": {},
            "time_range": None,
            "confidence": 0.0,
        }

    async def execute_and_respond(
        self, query: str, compute_func
    ) -> str:
        """
        Process query, compute metric, and return natural language response.

        Args:
            query: Natural language query
            compute_func: Function to compute metric values

        Returns:
            Natural language response
        """
        parsed = await self.process(query)

        if "error" in parsed or not parsed.get("metric_name"):
            return "I'm not sure how to answer that. Could you rephrase your question?"

        metric_name = parsed["metric_name"]
        dimensions = parsed.get("dimensions", {})
        time_range = parsed.get("time_range")

        try:
            df = await compute_func(metric_name, dimensions, self._parse_time_range(time_range))

            if df is None or df.is_empty():
                return f"I couldn't find any data for {metric_name}."

            response = await self._format_response(metric_name, df, dimensions)
            return response

        except Exception as e:
            return f"I encountered an error: {str(e)}"

    def _parse_time_range(self, time_range: str | None) -> tuple | None:
        """Parse time range string to datetime tuple."""
        from datetime import datetime, timedelta

        if not time_range:
            return None

        now = datetime.utcnow()

        range_map = {
            "today": (now.replace(hour=0, minute=0, second=0), now),
            "yesterday": (
                (now - timedelta(days=1)).replace(hour=0, minute=0, second=0),
                now.replace(hour=0, minute=0, second=0),
            ),
            "this_week": (now - timedelta(days=now.weekday()), now),
            "this_month": (now.replace(day=1), now),
            "last_7_days": (now - timedelta(days=7), now),
            "last_30_days": (now - timedelta(days=30), now),
        }

        return range_map.get(time_range)

    async def _format_response(
        self, metric_name: str, df, dimensions: dict[str, Any]
    ) -> str:
        """Format computed data as natural language response."""
        import polars as pl

        if "value" in df.columns:
            if len(df) == 1:
                value = df["value"][0]
                return f"The {metric_name} is {value:,.2f}."

            total = df["value"].sum()
            return f"The total {metric_name} is {total:,.2f} across {len(df)} records."

        return f"I found {len(df)} records for {metric_name}."
