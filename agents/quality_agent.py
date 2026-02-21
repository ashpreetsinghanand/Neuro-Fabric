"""
Data Quality Agent.

Runs comprehensive per-table quality analysis using the quality tools.
Produces completeness scores, null rates, statistical summaries, PK health,
and freshness metrics — stored in state.quality_report.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

from core.config import GEMINI_MODEL, GOOGLE_API_KEY
from core.state import AgentState, extract_message_content
from tools.quality_tools import QUALITY_TOOLS
from tools.schema_tools import get_columns

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are the Data Quality Agent for Neuro-Fabric, an AI-powered data dictionary platform.

Your sole responsibility is to perform thorough data quality analysis on each table in the database.

For each table provided to you, you MUST:
1. Call `compute_table_completeness` to get overall completeness and per-column null rates.
2. For each column, call `analyze_column_stats` to get distinct count, min, max, mean, stddev.
3. If the table has a primary key, call `check_pk_uniqueness` with those PK columns.
4. If you detect any timestamp/date column (names like created_at, updated_at, date, timestamp),
   call `check_freshness` using that column.

Compile results per table and return ONLY valid JSON (no markdown, no prose):
{
  "quality_report": {
    "<table_name>": {
      "table_name": "...",
      "row_count": <int>,
      "overall_completeness": <float 0-1>,
      "column_quality": [
        {
          "column_name": "...",
          "null_count": <int>,
          "null_rate": <float>,
          "distinct_count": <int>,
          "min_value": "...",
          "max_value": "...",
          "mean_value": <float or null>,
          "std_dev": <float or null>
        }
      ],
      "pk_uniqueness_rate": <float or null>,
      "freshness_column": "<col or null>",
      "freshness_latest": "<datetime or null>",
      "freshness_oldest": "<datetime or null>"
    }
  }
}
"""


def _build_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GOOGLE_API_KEY,
        temperature=0,
    )


def quality_agent_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node for data quality analysis."""
    logger.info("Quality Agent: starting analysis.")

    schema = state.get("schema", {})
    if not schema:
        logger.warning("Quality Agent: no schema available, skipping.")
        return {"quality_report": {}, "errors": ["QualityAgent: no schema to analyze."]}

    db_config = state.get("db_config", {})
    db_config_json = json.dumps(db_config)

    # Provide table list + schema summary in the prompt
    table_summary = json.dumps(
        {
            name: {
                "primary_keys": info.get("primary_keys", []),
                "columns": [
                    {"name": c["name"], "data_type": c.get("data_type") or c.get("type", "unknown")}
                    for c in info.get("columns", [])
                ],
            }
            for name, info in schema.items()
        },
        indent=2,
    )

    llm = _build_llm()
    # Attach schema tools as well (get_columns is useful for completeness tool)
    all_tools = QUALITY_TOOLS + [get_columns]
    agent = create_react_agent(llm, all_tools)

    user_message = HumanMessage(
        content=(
            f"Analyze data quality for the following tables. "
            f"Use db_config_json='{db_config_json}' for all tool calls.\n\n"
            f"Table metadata:\n{table_summary}\n\n"
            "Return a JSON object with key 'quality_report'."
        )
    )

    try:
        result = agent.invoke(
            {"messages": [SystemMessage(content=_SYSTEM_PROMPT), user_message]}
        )
        final_content = extract_message_content(result["messages"][-1].content)
        cleaned = final_content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()

        parsed = json.loads(cleaned)
        quality_report = parsed.get("quality_report", {})
        logger.info("Quality Agent: analyzed %d tables.", len(quality_report))
        return {"quality_report": quality_report}

    except Exception as exc:
        logger.error("Quality Agent failed: %s", exc)
        return {"quality_report": {}, "errors": [f"QualityAgent error: {exc}"]}
