"""
Export Agent.

Serializes the complete AgentState (schema + quality_report + documentation)
into JSON and Markdown artifacts on disk, then updates state.artifacts.
Also persists the schema cache for incremental update support.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from core.config import SCHEMA_CACHE_FILE
from core.state import AgentState

logger = logging.getLogger(__name__)


def _write_json(db_name: str, content: dict) -> str:
    from datetime import datetime
    from core.config import OUTPUTS_DIR

    filename = f"{db_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path = OUTPUTS_DIR / filename
    path.write_text(json.dumps(content, indent=2, default=str), encoding="utf-8")
    logger.info("JSON artifact: %s", path)
    return str(path)


def _write_markdown(db_name: str, schema: dict, quality: dict, docs: dict) -> str:
    from datetime import datetime
    from core.config import OUTPUTS_DIR

    lines: list[str] = [
        f"# Data Dictionary: {db_name}",
        f"\n_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n",
        "---\n",
        "## Table of Contents\n",
    ]

    for table_name in sorted(schema.keys()):
        lines.append(f"- [{table_name}](#{table_name.lower().replace(' ', '-')})")
    lines.append("\n---\n")

    for table_name in sorted(schema.keys()):
        table_schema = schema[table_name]
        doc = docs.get(table_name, {})
        qual = quality.get(table_name, {})

        lines.append(f"## Table: `{table_name}`\n")

        if doc.get("business_summary"):
            lines.append(f"> {doc['business_summary']}\n")

        # Quality metrics summary
        completeness = qual.get("overall_completeness")
        row_count = qual.get("row_count") or table_schema.get("row_count")
        pk_health = qual.get("pk_uniqueness_rate")
        freshness = qual.get("freshness_latest")

        lines.append("### Quality Metrics\n")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        if row_count is not None:
            lines.append(f"| Row Count | {row_count:,} |")
        if completeness is not None:
            lines.append(f"| Overall Completeness | {completeness * 100:.1f}% |")
        if pk_health is not None:
            lines.append(f"| PK Uniqueness | {pk_health * 100:.1f}% |")
        if freshness:
            lines.append(f"| Latest Record | {freshness} |")
        lines.append("")

        # Columns table
        columns = table_schema.get("columns", [])
        col_descriptions = doc.get("column_descriptions", {})
        col_quality: dict[str, dict] = {
            cq["column_name"]: cq for cq in qual.get("column_quality", [])
        }

        if columns:
            lines.append("### Columns\n")
            lines.append("| Column | Type | Nullable | PK | FK | Null Rate | Distinct | Description |")
            lines.append("|--------|------|----------|----|----|-----------|----------|-------------|")
            for col in columns:
                cq = col_quality.get(col["name"], {})
                pk = "✓" if col.get("is_primary_key") else ""
                fk = "✓" if col.get("is_foreign_key") else ""
                nullable = "Yes" if col.get("nullable") else "No"
                null_rate = f"{cq.get('null_rate', 0) * 100:.1f}%" if "null_rate" in cq else "-"
                distinct = str(cq.get("distinct_count", "-"))
                desc = col_descriptions.get(col["name"], "")
                dtype = col.get("data_type") or col.get("type", "unknown")
                lines.append(
                    f"| `{col['name']}` | `{dtype}` | {nullable} | {pk} | {fk} | {null_rate} | {distinct} | {desc} |"
                )
            lines.append("")

        # Relationships
        fks = table_schema.get("foreign_keys", [])
        if fks:
            lines.append("### Relationships\n")
            for fk in fks:
                lines.append(
                    f"- `{table_name}.{fk['column']}` → `{fk['ref_table']}.{fk['ref_column']}`"
                )
            lines.append("")

        # Related tables
        related = doc.get("related_tables", [])
        if related:
            lines.append(f"**Related Tables:** {', '.join(f'`{t}`' for t in related)}\n")

        # Usage recommendations
        recommendations = doc.get("usage_recommendations", [])
        if recommendations:
            lines.append("### Usage Recommendations\n")
            for rec in recommendations:
                lines.append(f"- {rec}")
            lines.append("")

        # Statistical highlights
        if qual.get("column_quality"):
            lines.append("### Statistical Highlights\n")
            lines.append("| Column | Min | Max | Mean | Std Dev |")
            lines.append("|--------|-----|-----|------|---------|")
            for cq in qual["column_quality"]:
                if cq.get("mean_value") is not None:
                    mean = f"{cq['mean_value']:.2f}" if cq["mean_value"] is not None else "-"
                    std = f"{cq['std_dev']:.2f}" if cq.get("std_dev") is not None else "-"
                    lines.append(
                        f"| `{cq['column_name']}` | {cq.get('min_value', '-')} | "
                        f"{cq.get('max_value', '-')} | {mean} | {std} |"
                    )
            lines.append("")

        # Suggested SQL
        queries = doc.get("suggested_queries", [])
        if queries:
            lines.append("### Suggested Queries\n")
            for q in queries:
                lines.append(f"```sql\n{q}\n```\n")

        lines.append("---\n")

    filename = f"{db_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    path = OUTPUTS_DIR / filename
    path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Markdown artifact: %s", path)
    return str(path)


def export_agent_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node for artifact export."""
    logger.info("Export Agent: writing artifacts.")

    schema = state.get("schema", {})
    quality = state.get("quality_report", {})
    docs = state.get("documentation", {})
    db_config = state.get("db_config", {})
    db_name = db_config.get("name", "database")

    artifacts: list[str] = list(state.get("artifacts", []))

    full_content = {
        "database": db_name,
        "schema": schema,
        "quality_report": quality,
        "documentation": docs,
    }

    errors: list[str] = list(state.get("errors", []))

    try:
        json_path = _write_json(db_name, full_content)
        artifacts.append(json_path)
    except Exception as exc:
        logger.error("Export Agent JSON write failed: %s", exc)
        errors.append(f"ExportAgent JSON error: {exc}")

    try:
        md_path = _write_markdown(db_name, schema, quality, docs)
        artifacts.append(md_path)
    except Exception as exc:
        logger.error("Export Agent Markdown write failed: %s", exc)
        errors.append(f"ExportAgent Markdown error: {exc}")

    # Persist schema cache for incremental updates
    try:
        SCHEMA_CACHE_FILE.write_text(
            json.dumps(schema, indent=2, default=str), encoding="utf-8"
        )
        logger.info("Schema cache updated: %s", SCHEMA_CACHE_FILE)
    except Exception as exc:
        logger.warning("Failed to update schema cache: %s", exc)

    logger.info("Export Agent: %d artifacts written.", len(artifacts))
    return {"artifacts": artifacts, "errors": errors}
