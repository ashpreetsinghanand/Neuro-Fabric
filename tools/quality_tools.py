"""
LangChain tools for data quality analysis.
Performs per-column and per-table statistical analysis via SQL.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.tools import tool
from sqlalchemy import text

from core.db_connectors import get_engine

logger = logging.getLogger(__name__)


def _engine(db_config: dict):
    return get_engine(db_config or {})


# ---------------------------------------------------------------------------
# Tool: analyze_column_nulls
# ---------------------------------------------------------------------------

@tool
def analyze_column_nulls(
    table_name: str,
    column_name: str,
    schema_name: str = "public",
    db_config_json: str = "{}",
) -> str:
    """
    Compute null count and null rate for a specific column.

    Args:
        table_name: Target table.
        column_name: Column to analyze.
        schema_name: Schema containing the table (default: 'public').
        db_config_json: JSON string with optional db connection config.

    Returns:
        JSON with null_count, total_rows, null_rate.
    """
    db_config = json.loads(db_config_json)
    engine = _engine(db_config)
    try:
        q = text(
            f"""
            SELECT
                COUNT(*) AS total_rows,
                COUNT(*) FILTER (WHERE "{column_name}" IS NULL) AS null_count
            FROM "{schema_name}"."{table_name}"
            """
        )
        with engine.connect() as conn:
            row = conn.execute(q).mappings().one()
        total = row["total_rows"] or 1
        null_count = row["null_count"]
        return json.dumps({
            "table": table_name,
            "column": column_name,
            "total_rows": total,
            "null_count": null_count,
            "null_rate": round(null_count / total, 4),
        })
    except Exception as exc:
        logger.error("analyze_column_nulls failed: %s", exc)
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Tool: analyze_column_stats
# ---------------------------------------------------------------------------

@tool
def analyze_column_stats(
    table_name: str,
    column_name: str,
    schema_name: str = "public",
    db_config_json: str = "{}",
) -> str:
    """
    Compute distinct count, min, max, mean, and stddev for a column.
    Numeric statistics are only returned for numeric/date columns.

    Args:
        table_name: Target table.
        column_name: Column to analyze.
        schema_name: Schema containing the table (default: 'public').
        db_config_json: JSON string with optional db connection config.

    Returns:
        JSON with distinct_count, min_value, max_value, mean_value, std_dev.
    """
    db_config = json.loads(db_config_json)
    engine = _engine(db_config)
    try:
        # Cast-safe approach: attempt numeric stats, catch if non-numeric
        q_base = text(
            f"""
            SELECT
                COUNT(DISTINCT "{column_name}") AS distinct_count,
                MIN("{column_name}"::text) AS min_value,
                MAX("{column_name}"::text) AS max_value
            FROM "{schema_name}"."{table_name}"
            """
        )
        q_numeric = text(
            f"""
            SELECT
                AVG("{column_name}"::numeric) AS mean_value,
                STDDEV("{column_name}"::numeric) AS std_dev
            FROM "{schema_name}"."{table_name}"
            """
        )
        with engine.connect() as conn:
            base_row = conn.execute(q_base).mappings().one()
            try:
                num_row = conn.execute(q_numeric).mappings().one()
                mean_value = float(num_row["mean_value"]) if num_row["mean_value"] is not None else None
                std_dev = float(num_row["std_dev"]) if num_row["std_dev"] is not None else None
            except Exception:
                mean_value = None
                std_dev = None

        return json.dumps({
            "table": table_name,
            "column": column_name,
            "distinct_count": base_row["distinct_count"],
            "min_value": base_row["min_value"],
            "max_value": base_row["max_value"],
            "mean_value": mean_value,
            "std_dev": std_dev,
        })
    except Exception as exc:
        logger.error("analyze_column_stats failed: %s", exc)
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Tool: check_pk_uniqueness
# ---------------------------------------------------------------------------

@tool
def check_pk_uniqueness(
    table_name: str,
    pk_columns: str,
    schema_name: str = "public",
    db_config_json: str = "{}",
) -> str:
    """
    Check primary key uniqueness health: fraction of rows with unique PK values.

    Args:
        table_name: Target table.
        pk_columns: Comma-separated list of PK column names.
        schema_name: Schema containing the table (default: 'public').
        db_config_json: JSON string with optional db connection config.

    Returns:
        JSON with total_rows, unique_pk_rows, uniqueness_rate.
    """
    db_config = json.loads(db_config_json)
    engine = _engine(db_config)
    cols = [c.strip() for c in pk_columns.split(",")]
    col_expr = ", ".join(f'"{c}"' for c in cols)
    try:
        q = text(
            f"""
            SELECT
                COUNT(*) AS total_rows,
                COUNT(*) OVER () - COUNT(*) AS duplicate_count,
                (SELECT COUNT(*) FROM (
                    SELECT {col_expr} FROM "{schema_name}"."{table_name}"
                    GROUP BY {col_expr}
                ) AS t) AS unique_pk_rows
            FROM "{schema_name}"."{table_name}"
            LIMIT 1
            """
        )
        # Simpler alternative for all DB types
        q2 = text(
            f"""
            SELECT
                (SELECT COUNT(*) FROM "{schema_name}"."{table_name}") AS total_rows,
                (SELECT COUNT(*) FROM (
                    SELECT {col_expr} FROM "{schema_name}"."{table_name}"
                    GROUP BY {col_expr}
                ) AS sub) AS unique_pk_rows
            """
        )
        with engine.connect() as conn:
            row = conn.execute(q2).mappings().one()
        total = row["total_rows"] or 1
        unique = row["unique_pk_rows"]
        return json.dumps({
            "table": table_name,
            "pk_columns": cols,
            "total_rows": total,
            "unique_pk_rows": unique,
            "uniqueness_rate": round(unique / total, 4),
        })
    except Exception as exc:
        logger.error("check_pk_uniqueness failed: %s", exc)
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Tool: check_freshness
# ---------------------------------------------------------------------------

@tool
def check_freshness(
    table_name: str,
    timestamp_column: str,
    schema_name: str = "public",
    db_config_json: str = "{}",
) -> str:
    """
    Check data freshness using a timestamp column: latest and oldest records.

    Args:
        table_name: Target table.
        timestamp_column: The datetime/timestamp column to use.
        schema_name: Schema containing the table (default: 'public').
        db_config_json: JSON string with optional db connection config.

    Returns:
        JSON with latest_record, oldest_record, age_days.
    """
    db_config = json.loads(db_config_json)
    engine = _engine(db_config)
    try:
        q = text(
            f"""
            SELECT
                MAX("{timestamp_column}") AS latest_record,
                MIN("{timestamp_column}") AS oldest_record,
                EXTRACT(EPOCH FROM (NOW() - MAX("{timestamp_column}"))) / 86400 AS age_days
            FROM "{schema_name}"."{table_name}"
            """
        )
        with engine.connect() as conn:
            row = conn.execute(q).mappings().one()
        return json.dumps({
            "table": table_name,
            "timestamp_column": timestamp_column,
            "latest_record": str(row["latest_record"]) if row["latest_record"] else None,
            "oldest_record": str(row["oldest_record"]) if row["oldest_record"] else None,
            "age_days": float(row["age_days"]) if row["age_days"] is not None else None,
        })
    except Exception as exc:
        logger.error("check_freshness failed: %s", exc)
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Tool: compute_table_completeness
# ---------------------------------------------------------------------------

@tool
def compute_table_completeness(
    table_name: str,
    schema_name: str = "public",
    db_config_json: str = "{}",
) -> str:
    """
    Compute overall table completeness: average non-null rate across all columns.

    Args:
        table_name: Target table.
        schema_name: Schema containing the table (default: 'public').
        db_config_json: JSON string with optional db connection config.

    Returns:
        JSON with overall_completeness (0.0–1.0) and per-column null rates.
    """
    db_config = json.loads(db_config_json)
    engine = _engine(db_config)
    from core.db_connectors import get_inspector
    inspector = get_inspector(engine)
    try:
        columns = [c["name"] for c in inspector.get_columns(table_name, schema=schema_name)]
        null_rate_exprs = ",\n".join(
            f'AVG(CASE WHEN "{c}" IS NULL THEN 1.0 ELSE 0.0 END) AS "{c}_null_rate"'
            for c in columns
        )
        q = text(
            f"""
            SELECT
                COUNT(*) AS total_rows,
                {null_rate_exprs}
            FROM "{schema_name}"."{table_name}"
            """
        )
        with engine.connect() as conn:
            row = dict(conn.execute(q).mappings().one())

        per_col_null_rates: dict[str, float] = {}
        for c in columns:
            key = f"{c}_null_rate"
            val = row.get(key)
            per_col_null_rates[c] = round(float(val), 4) if val is not None else 0.0

        overall = 1.0 - (sum(per_col_null_rates.values()) / len(per_col_null_rates)) if per_col_null_rates else 1.0

        return json.dumps({
            "table": table_name,
            "total_rows": row.get("total_rows"),
            "overall_completeness": round(overall, 4),
            "column_null_rates": per_col_null_rates,
        })
    except Exception as exc:
        logger.error("compute_table_completeness failed: %s", exc)
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# All quality tools
# ---------------------------------------------------------------------------

QUALITY_TOOLS = [
    analyze_column_nulls,
    analyze_column_stats,
    check_pk_uniqueness,
    check_freshness,
    compute_table_completeness,
]
