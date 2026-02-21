"""
Conversational Chat Agent.

Handles natural language questions about the database schema, data quality,
and generates SQL suggestions. Uses the documented schema context from state
plus the Supabase MCP and SQL execution tools for live queries.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

from core.config import GEMINI_MODEL, GOOGLE_API_KEY
from core.state import AgentState
from tools.schema_tools import get_columns, list_tables
from tools.sql_tools import SQL_TOOLS

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are the Conversational Data Assistant for Neuro-Fabric, an enterprise data dictionary platform.

You have access to:
1. A comprehensive data dictionary (provided as context below) with schema metadata,
   data quality metrics, and AI-generated business descriptions for every table.
2. SQL execution tools to run live queries against the database.
3. Schema browsing tools to look up column details on demand.

You help business analysts, data engineers, and non-technical users:
- Understand what specific tables and columns mean in business terms
- Discover relationships between tables
- Write SQL queries to answer their business questions
- Identify data quality issues and interpret quality metrics
- Navigate the database schema intuitively

Guidelines:
- Always explain SQL queries you generate in plain English
- If a question is ambiguous, clarify before querying
- Cite the data dictionary context when answering definitional questions
- For SQL suggestions, use double-quoted identifiers (e.g. "table_name"."column_name")
- If data quality issues are relevant, proactively mention them
- Keep answers concise but complete

IMPORTANT: You are an assistant for reading/understanding data only. 
Never generate INSERT, UPDATE, DELETE, DROP, or DDL statements.
"""


def _build_context(state: AgentState) -> str:
    """Build a compact context string from the current state for the system prompt."""
    schema = state.get("schema", {})
    docs = state.get("documentation", {})
    quality = state.get("quality_report", {})

    if not schema:
        return "No schema has been loaded yet. Ask the user to run the schema extraction first."

    lines = ["## Available Tables\n"]
    for table_name in sorted(schema.keys()):
        doc = docs.get(table_name, {})
        qual = quality.get(table_name, {})
        summary = doc.get("business_summary", "No description available.")
        row_count = qual.get("row_count") or schema[table_name].get("row_count", "unknown")
        completeness = qual.get("overall_completeness")
        completeness_str = f"{completeness * 100:.1f}%" if completeness is not None else "N/A"

        cols = schema[table_name].get("columns", [])
        col_names = [c["name"] for c in cols]
        col_descriptions = doc.get("column_descriptions", {})

        lines.append(f"### `{table_name}`")
        lines.append(f"**Summary:** {summary}")
        lines.append(f"**Rows:** {row_count:,}" if isinstance(row_count, int) else f"**Rows:** {row_count}")
        lines.append(f"**Completeness:** {completeness_str}")
        lines.append("**Columns:**")
        for col in cols[:20]:  # cap to avoid huge context
            desc = col_descriptions.get(col["name"], "")
            pk = " [PK]" if col.get("is_primary_key") else ""
            fk = " [FK]" if col.get("is_foreign_key") else ""
            lines.append(f"  - `{col['name']}` ({col['data_type']}){pk}{fk}: {desc}")
        if len(cols) > 20:
            lines.append(f"  - ... and {len(cols) - 20} more columns")
        lines.append("")

    return "\n".join(lines)


def _build_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GOOGLE_API_KEY,
        temperature=0.1,
    )


def chat_agent_node(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node for conversational Q&A.
    Processes the latest human message and appends an AI response.
    """
    messages = state.get("messages", [])
    db_config = state.get("db_config", {})
    db_config_json = json.dumps(db_config)

    # Get the last human message
    human_messages = [m for m in messages if isinstance(m, HumanMessage)]
    if not human_messages:
        return {"messages": [AIMessage(content="Hello! I'm your data dictionary assistant. How can I help you explore your database?")]}

    last_human = human_messages[-1]

    # Build context from documented schema
    context = _build_context(state)

    system_with_context = f"{_SYSTEM_PROMPT}\n\n---\n## Data Dictionary Context\n\n{context}"

    llm = _build_llm()
    chat_tools = SQL_TOOLS + [list_tables, get_columns]
    agent = create_react_agent(llm, chat_tools)

    # Build the full message history for continuity
    agent_messages = [SystemMessage(content=system_with_context)]
    for msg in messages[-10:]:  # keep last 10 messages for context window management
        agent_messages.append(msg)

    # Inject db_config hint into the user message if tools will be needed
    augmented_content = (
        f"{last_human.content}\n\n"
        f"[System note: Use db_config_json='{db_config_json}' for any tool calls.]"
    )
    agent_messages[-1] = HumanMessage(content=augmented_content)

    try:
        result = agent.invoke({"messages": agent_messages})
        ai_response = result["messages"][-1].content
        return {"messages": [AIMessage(content=ai_response)]}
    except Exception as exc:
        logger.error("Chat Agent failed: %s", exc)
        error_msg = f"I encountered an error processing your request: {exc}. Please try rephrasing your question."
        return {"messages": [AIMessage(content=error_msg)]}
