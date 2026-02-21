"""
LangChain tools for exporting documentation artifacts to disk.
Writes JSON and Markdown files into the /outputs directory.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from langchain_core.tools import tool

from core.config import OUTPUTS_DIR

logger = logging.getLogger(__name__)


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# ---------------------------------------------------------------------------
# Tool: write_json_artifact
# ---------------------------------------------------------------------------

@tool
def write_json_artifact(db_name: str, content_json: str) -> str:
    """
    Write a full data dictionary as a JSON artifact to disk.

    Args:
        db_name: Identifier for the database/project (used in filename).
        content_json: JSON-serialized dictionary containing schema,
                      quality_report, and documentation.

    Returns:
        JSON with the output file path.
    """
    try:
        content = json.loads(content_json)
        filename = f"{db_name}_{_timestamp()}.json"
        path = OUTPUTS_DIR / filename
        path.write_text(json.dumps(content, indent=2, default=str), encoding="utf-8")
        logger.info("JSON artifact written: %s", path)
        return json.dumps({"status": "success", "path": str(path)})
    except Exception as exc:
        logger.error("write_json_artifact failed: %s", exc)
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Tool: write_markdown_artifact
# ---------------------------------------------------------------------------

@tool
def write_markdown_artifact(db_name: str, content_json: str) -> str:
    """
    Generate and write a human-readable Markdown data dictionary.

    Args:
        db_name: Identifier for the database/project (used in filename).
        content_json: JSON-serialized dictionary containing schema,
                      quality_report, and documentation keyed by table name.

    Returns:
        JSON with the output file path.
    """
    try:
        content = json.loads(content_json)
        schema: dict = content.get("schema", {})
        quality: dict = content.get("quality_report", {})
        docs: dict = content.get("documentation", {})

        lines: list[str] = [
            f"# Data Dictionary: {db_name}",
            f"\n_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n",
            "---\n",
        ]

        for table_name, table_schema in schema.items():
            doc = docs.get(table_name, {})
            qual = quality.get(table_name, {})

            lines.append(f"## Table: `{table_name}`\n")

            # Business summary
            if doc.get("business_summary"):
                lines.append(f"**Business Summary:** {doc['business_summary']}\n")

            # Quality overview
            completeness = qual.get("overall_completeness")
            row_count = qual.get("row_count") or table_schema.get("row_count")
            if completeness is not None:
                lines.append(f"**Completeness:** {completeness * 100:.1f}%")
            if row_count is not None:
                lines.append(f"**Row Count:** {row_count:,}")

            freshness_latest = qual.get("freshness_latest")
            if freshness_latest:
                lines.append(f"**Latest Record:** {freshness_latest}")
            lines.append("")

            # Columns table
            columns = table_schema.get("columns", [])
            if columns:
                lines.append("### Columns\n")
                lines.append("| Column | Type | Nullable | PK | FK | Description |")
                lines.append("|--------|------|----------|----|----|-------------|")
                col_descriptions = doc.get("column_descriptions", {})
                for col in columns:
                    pk = "✓" if col.get("is_primary_key") else ""
                    fk = "✓" if col.get("is_foreign_key") else ""
                    nullable = "Yes" if col.get("nullable") else "No"
                    desc = col_descriptions.get(col["name"], "")
                    lines.append(
                        f"| `{col['name']}` | {col['data_type']} | {nullable} | {pk} | {fk} | {desc} |"
                    )
                lines.append("")

            # FK relationships
            fks = table_schema.get("foreign_keys", [])
            if fks:
                lines.append("### Relationships\n")
                for fk in fks:
                    lines.append(
                        f"- `{fk['column']}` → `{fk['ref_table']}.{fk['ref_column']}`"
                    )
                lines.append("")

            # Usage recommendations
            recommendations = doc.get("usage_recommendations", [])
            if recommendations:
                lines.append("### Usage Recommendations\n")
                for rec in recommendations:
                    lines.append(f"- {rec}")
                lines.append("")

            # Suggested SQL queries
            queries = doc.get("suggested_queries", [])
            if queries:
                lines.append("### Suggested Queries\n")
                for q in queries:
                    lines.append(f"```sql\n{q}\n```\n")

            lines.append("---\n")

        filename = f"{db_name}_{_timestamp()}.md"
        path = OUTPUTS_DIR / filename
        path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Markdown artifact written: %s", path)
        return json.dumps({"status": "success", "path": str(path)})
    except Exception as exc:
        logger.error("write_markdown_artifact failed: %s", exc)
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Tool: write_schema_cache
# ---------------------------------------------------------------------------

@tool
def write_schema_cache(content_json: str) -> str:
    """
    Persist the current schema snapshot to a cache file for incremental update detection.

    Args:
        content_json: JSON-serialized schema dict.

    Returns:
        JSON with cache file path.
    """
    from core.config import SCHEMA_CACHE_FILE
    try:
        content = json.loads(content_json)
        SCHEMA_CACHE_FILE.write_text(json.dumps(content, indent=2, default=str), encoding="utf-8")
        return json.dumps({"status": "success", "path": str(SCHEMA_CACHE_FILE)})
    except Exception as exc:
        logger.error("write_schema_cache failed: %s", exc)
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# All export tools
# ---------------------------------------------------------------------------

EXPORT_TOOLS = [
    write_json_artifact,
    write_markdown_artifact,
    write_schema_cache,
]
