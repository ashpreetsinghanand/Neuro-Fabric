"""
LangChain tools for SQL execution and query suggestion.
Used by the Conversational Chat Agent.
"""

from __future__ import annotations

import json
import logging

from langchain_core.tools import tool
from sqlalchemy import text

from core.db_connectors import get_engine

logger = logging.getLogger(__name__)


@tool
def execute_query(sql: str, db_config_json: str = "{}") -> str:
    """
    Execute a read-only SQL SELECT query against the database and return results.

    Args:
        sql: A valid SQL SELECT statement to execute.
        db_config_json: JSON string with optional db connection config.

    Returns:
        JSON with rows (list of dicts) and column names, capped at 100 rows.
    """
    db_config = json.loads(db_config_json) if db_config_json else {}
    # Safety: only allow SELECT statements
    normalized = sql.strip().upper()
    if not normalized.startswith("SELECT") and not normalized.startswith("WITH"):
        return json.dumps({"error": "Only SELECT/WITH queries are permitted."})

    engine = get_engine(db_config)
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            columns = list(result.keys())
            rows = [dict(zip(columns, row)) for row in result.fetchmany(100)]
        return json.dumps({
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "capped_at": 100,
        }, default=str)
    except Exception as exc:
        logger.error("execute_query failed: %s", exc)
        return json.dumps({"error": str(exc)})


@tool
def get_sample_rows(
    table_name: str,
    schema_name: str = "public",
    limit: int = 5,
    db_config_json: str = "{}",
) -> str:
    """
    Fetch a small sample of rows from a table for context.

    Args:
        table_name: The table to sample from.
        schema_name: Schema containing the table (default: 'public').
        limit: Number of sample rows to return (max 20).
        db_config_json: JSON string with optional db connection config.

    Returns:
        JSON with sample rows and column names.
    """
    db_config = json.loads(db_config_json) if db_config_json else {}
    limit = min(limit, 20)
    engine = get_engine(db_config)
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text(f'SELECT * FROM "{schema_name}"."{table_name}" LIMIT {limit}')
            )
            columns = list(result.keys())
            rows = [dict(zip(columns, row)) for row in result.fetchall()]
        return json.dumps({"table": table_name, "columns": columns, "rows": rows}, default=str)
    except Exception as exc:
        logger.error("get_sample_rows failed: %s", exc)
        return json.dumps({"error": str(exc)})


SQL_TOOLS = [execute_query, get_sample_rows]
