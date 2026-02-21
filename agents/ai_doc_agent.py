"""
AI Documentation Agent.

Uses Gemini 3 Pro Preview to generate rich, business-friendly documentation
for each table: business summaries, column descriptions, usage recommendations,
related table suggestions, and sample SQL queries.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from core.config import GEMINI_MODEL, GOOGLE_API_KEY
from core.state import AgentState

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are the AI Documentation Agent for Neuro-Fabric, an enterprise data dictionary platform.

Your role is to translate raw technical database metadata into clear, business-friendly documentation.

For EACH table provided, generate:
1. **business_summary** – A 2-4 sentence plain-English description of what the table represents,
   what business process it supports, and who typically uses it.
2. **column_descriptions** – A dict mapping each column name to a 1-sentence business description.
   Infer meaning from the column name, data type, and any FK relationships.
3. **usage_recommendations** – 3-5 bullet points advising analysts on how to correctly use this table:
   common join patterns, filters, aggregations, and any data quality caveats.
4. **related_tables** – List of other table names that this table is logically connected to
   (via FKs or inferred domain relationships).
5. **suggested_queries** – 2-3 useful SQL SELECT queries showcasing common business questions
   this table can answer. Use proper quoting for identifiers.

Return ONLY valid JSON (no markdown fences, no prose outside the JSON):
{
  "documentation": {
    "<table_name>": {
      "table_name": "...",
      "business_summary": "...",
      "column_descriptions": {"col1": "...", "col2": "..."},
      "usage_recommendations": ["...", "..."],
      "related_tables": ["...", "..."],
      "suggested_queries": ["SELECT ...", "SELECT ..."]
    }
  }
}
"""


def _build_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GOOGLE_API_KEY,
        temperature=0.2,  # slight creativity for business descriptions
    )


def _batch_tables(schema: dict, quality: dict, batch_size: int = 10) -> list[str]:
    """Split tables into batches for context-window management."""
    tables = list(schema.keys())
    batches = []
    for i in range(0, len(tables), batch_size):
        batch = tables[i : i + batch_size]
        payload = {
            name: {
                "schema": schema[name],
                "quality": quality.get(name, {}),
            }
            for name in batch
        }
        batches.append(json.dumps(payload, indent=2, default=str))
    return batches


def ai_doc_agent_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node for AI documentation generation."""
    logger.info("AI Doc Agent: starting documentation generation.")

    schema = state.get("schema", {})
    quality = state.get("quality_report", {})

    if not schema:
        logger.warning("AI Doc Agent: no schema available.")
        return {"documentation": {}, "errors": ["AIDocAgent: no schema to document."]}

    llm = _build_llm()
    all_documentation: dict = {}

    batches = _batch_tables(schema, quality)
    logger.info("AI Doc Agent: processing %d tables in %d batch(es).", len(schema), len(batches))

    for idx, batch_json in enumerate(batches):
        logger.info("AI Doc Agent: processing batch %d/%d.", idx + 1, len(batches))
        user_message = HumanMessage(
            content=(
                "Generate business-friendly documentation for the following database tables.\n\n"
                f"Table metadata (schema + quality metrics):\n{batch_json}\n\n"
                "Return ONLY the JSON object with key 'documentation'."
            )
        )
        try:
            response = llm.invoke(
                [SystemMessage(content=_SYSTEM_PROMPT), user_message]
            )
            response_content = response.content
            if isinstance(response_content, list):
                response_content = response_content[0] if response_content else ""
            elif not isinstance(response_content, str):
                response_content = str(response_content)
                
            content = response_content.strip()

            # Strip markdown fences if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            parsed = json.loads(content)
            batch_docs = parsed.get("documentation", {})
            all_documentation.update(batch_docs)
            logger.info(
                "AI Doc Agent: documented %d tables in batch %d.", len(batch_docs), idx + 1
            )
        except Exception as exc:
            logger.error("AI Doc Agent batch %d failed: %s", idx + 1, exc)
            # Continue with other batches; log error
            errors = state.get("errors", [])
            errors.append(f"AIDocAgent batch {idx+1} error: {exc}")

    logger.info("AI Doc Agent: total documented tables: %d.", len(all_documentation))
    return {"documentation": all_documentation}
