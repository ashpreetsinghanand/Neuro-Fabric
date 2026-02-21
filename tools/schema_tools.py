"""
LangChain tools for schema extraction.
Each tool operates against the default engine (DuckDB or Postgres).
"""
from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.tools import tool

from core.db_connectors import DuckDBEngine, get_engine, get_inspector, list_schemas

logger = logging.getLogger(__name__)


def _get_engine(db_config: dict | None = None):
    return get_engine(db_config)


def _default_schema(engine) -> str:
    """Return default schema name for the engine type."""
    if isinstance(engine, DuckDBEngine):
        return "main"
    return "public"


# ---------------------------------------------------------------------------
# Tool: list_tables
# ---------------------------------------------------------------------------

@tool
def list_tables(schema_name: str = "", db_config_json: str = "{}") -> str:
    """
    List all user tables in the specified database schema.

    Args:
        schema_name: The schema to inspect (leave empty for default).
        db_config_json: JSON string with optional db connection config.

    Returns:
        JSON list of table names.
    """
    db_config = json.loads(db_config_json) if db_config_json else {}
    engine = _get_engine(db_config)
    schema_name = schema_name or _default_schema(engine)
    inspector = get_inspector(engine)
    try:
        tables = inspector.get_table_names(schema=schema_name)
        return json.dumps({"schema": schema_name, "tables": tables})
    except Exception as exc:
        logger.error("list_tables failed: %s", exc)
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Tool: list_schemas
# ---------------------------------------------------------------------------

@tool
def list_all_schemas(db_config_json: str = "{}") -> str:
    """
    List all non-system schemas in the connected database.

    Args:
        db_config_json: JSON string with optional db connection config.

    Returns:
        JSON list of schema names.
    """
    db_config = json.loads(db_config_json) if db_config_json else {}
    engine = _get_engine(db_config)
    try:
        schemas = list_schemas(engine)
        return json.dumps({"schemas": schemas})
    except Exception as exc:
        logger.error("list_all_schemas failed: %s", exc)
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Tool: get_columns
# ---------------------------------------------------------------------------

@tool
def get_columns(table_name: str, schema_name: str = "", db_config_json: str = "{}") -> str:
    """
    Get all column definitions for a given table including data type,
    nullability, default, and primary key membership.

    Args:
        table_name: The table to inspect.
        schema_name: The schema containing the table (leave empty for default).
        db_config_json: JSON string with optional db connection config.

    Returns:
        JSON object with column metadata.
    """
    db_config = json.loads(db_config_json) if db_config_json else {}
    engine = _get_engine(db_config)
    schema_name = schema_name or _default_schema(engine)
    inspector = get_inspector(engine)
    try:
        columns = inspector.get_columns(table_name, schema=schema_name)
        pk_constraint = inspector.get_pk_constraint(table_name, schema=schema_name)
        pk_cols = set(pk_constraint.get("constrained_columns", []))

        result: list[dict[str, Any]] = []
        for col in columns:
            result.append({
                "name": col["name"],
                "data_type": str(col.get("type", col.get("data_type", "UNKNOWN"))),
                "nullable": col.get("nullable", True),
                "default": str(col.get("default")) if col.get("default") is not None else None,
                "is_primary_key": col["name"] in pk_cols,
            })
        return json.dumps({"table": table_name, "schema": schema_name, "columns": result})
    except Exception as exc:
        logger.error("get_columns failed for %s: %s", table_name, exc)
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Tool: get_foreign_keys
# ---------------------------------------------------------------------------

@tool
def get_foreign_keys(table_name: str, schema_name: str = "", db_config_json: str = "{}") -> str:
    """
    Retrieve all foreign key relationships for a table.

    Args:
        table_name: The table to inspect.
        schema_name: The schema containing the table (leave empty for default).
        db_config_json: JSON string with optional db connection config.

    Returns:
        JSON list of foreign key definitions.
    """
    db_config = json.loads(db_config_json) if db_config_json else {}
    engine = _get_engine(db_config)
    schema_name = schema_name or _default_schema(engine)
    inspector = get_inspector(engine)
    try:
        fks = inspector.get_foreign_keys(table_name, schema=schema_name)
        result = []
        for fk in fks:
            for local_col, ref_col in zip(
                fk.get("constrained_columns", []),
                fk.get("referred_columns", []),
            ):
                result.append({
                    "column": local_col,
                    "ref_table": fk.get("referred_table"),
                    "ref_schema": fk.get("referred_schema", schema_name),
                    "ref_column": ref_col,
                    "name": fk.get("name"),
                })
        return json.dumps({"table": table_name, "foreign_keys": result})
    except Exception as exc:
        logger.error("get_foreign_keys failed for %s: %s", table_name, exc)
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Tool: get_constraints
# ---------------------------------------------------------------------------

@tool
def get_constraints(table_name: str, schema_name: str = "", db_config_json: str = "{}") -> str:
    """
    Get all constraints (primary key, unique, check) and indexes for a table.

    Args:
        table_name: The table to inspect.
        schema_name: The schema containing the table (leave empty for default).
        db_config_json: JSON string with optional db connection config.

    Returns:
        JSON object with pk, unique constraints, check constraints, and indexes.
    """
    db_config = json.loads(db_config_json) if db_config_json else {}
    engine = _get_engine(db_config)
    schema_name = schema_name or _default_schema(engine)
    inspector = get_inspector(engine)
    try:
        pk = inspector.get_pk_constraint(table_name, schema=schema_name)
        unique = inspector.get_unique_constraints(table_name, schema=schema_name)
        check = inspector.get_check_constraints(table_name, schema=schema_name)
        indexes = inspector.get_indexes(table_name, schema=schema_name)

        return json.dumps({
            "table": table_name,
            "primary_key": pk,
            "unique_constraints": unique,
            "check_constraints": check,
            "indexes": indexes,
        })
    except Exception as exc:
        logger.error("get_constraints failed for %s: %s", table_name, exc)
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Tool: get_table_row_count
# ---------------------------------------------------------------------------

@tool
def get_table_row_count(table_name: str, schema_name: str = "", db_config_json: str = "{}") -> str:
    """
    Get the approximate row count for a table using a fast query.

    Args:
        table_name: The table to count.
        schema_name: The schema containing the table (leave empty for default).
        db_config_json: JSON string with optional db connection config.

    Returns:
        JSON object with row count.
    """
    db_config = json.loads(db_config_json) if db_config_json else {}
    engine = _get_engine(db_config)
    schema_name = schema_name or _default_schema(engine)
    try:
        with engine.connect() as conn:
            sql = f'SELECT COUNT(*) FROM "{schema_name}"."{table_name}"'
            result = conn.execute(sql)
            rows = result.fetchone()
            count = rows[0] if rows else 0
        return json.dumps({"table": table_name, "row_count": count})
    except Exception as exc:
        logger.error("get_table_row_count failed for %s: %s", table_name, exc)
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# All tools exported as a list for agent binding
# ---------------------------------------------------------------------------

SCHEMA_TOOLS = [
    list_all_schemas,
    list_tables,
    get_columns,
    get_foreign_keys,
    get_constraints,
    get_table_row_count,
]
