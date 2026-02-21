"""
Schema Extraction Agent.

Traverses all schemas and tables in the connected database using the
schema tools, then assembles the full metadata into state.schema.

This agent runs as a LangGraph node: it receives AgentState, performs
its work (possibly multiple LLM + tool call rounds), and returns a
state patch with the populated `schema` dict.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

from core.config import GEMINI_MODEL, GOOGLE_API_KEY, SCHEMA_CACHE_FILE
from core.state import AgentState
from tools.schema_tools import SCHEMA_TOOLS

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are the Schema Extraction Agent for Neuro-Fabric, an AI-powered data dictionary platform.

Your sole responsibility is to extract COMPLETE schema metadata from the connected database.

Steps you MUST follow:
1. Call `list_all_schemas` to discover all non-system schemas.
2. For each schema, call `list_tables` to get all tables.
3. For every table, call:
   a. `get_columns` – column names, types, nullability, defaults, PK membership
   b. `get_foreign_keys` – FK references
   c. `get_constraints` – PKs, unique constraints, check constraints, indexes
   d. `get_table_row_count` – approximate row count
4. Compile everything into a single JSON object keyed by "schema.table_name".

When done, output ONLY valid JSON in this exact structure (no markdown, no prose):
{
  "schema": {
    "<table_name>": {
      "table_name": "...",
      "schema_name": "...",
      "columns": [...],
      "primary_keys": [...],
      "foreign_keys": [...],
      "unique_constraints": [...],
      "indexes": [...],
      "row_count": <int>
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


def _schema_hash(schema: dict) -> str:
    return hashlib.md5(json.dumps(schema, sort_keys=True, default=str).encode()).hexdigest()


def _load_cached_schema() -> dict | None:
    if SCHEMA_CACHE_FILE.exists():
        try:
            return json.loads(SCHEMA_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def schema_agent_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node for schema extraction."""
    logger.info("Schema Agent: starting extraction.")

    db_config = state.get("db_config", {})
    db_config_json = json.dumps(db_config)

    llm = _build_llm()
    agent = create_react_agent(llm, SCHEMA_TOOLS)

    user_message = HumanMessage(
        content=(
            f"Extract the full schema from the database. "
            f"Use db_config_json='{db_config_json}' for all tool calls. "
            "Return a JSON object with key 'schema' containing all table metadata."
        )
    )

    try:
        result = agent.invoke(
            {"messages": [SystemMessage(content=_SYSTEM_PROMPT), user_message]}
        )
        # Extract the last AI message content
        final_content = result["messages"][-1].content

        if isinstance(final_content, list):
            final_content = final_content[0] if final_content else ""
        elif not isinstance(final_content, str):
            final_content = str(final_content)
            
        # Parse the JSON output from the agent
        # Agent may wrap in markdown code fences
        cleaned = final_content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()

        parsed = json.loads(cleaned)
        schema = parsed.get("schema", {})

        # Incremental update: check if schema changed
        cached = _load_cached_schema()
        if cached and _schema_hash(cached) == _schema_hash(schema):
            logger.info("Schema Agent: no schema changes detected, using cached version.")
            schema = cached

        logger.info("Schema Agent: extracted %d tables.", len(schema))
        return {"schema": schema, "errors": []}

    except Exception as exc:
        logger.error("Schema Agent failed: %s", exc)
        return {"schema": {}, "errors": [f"SchemaAgent error: {exc}"]}
