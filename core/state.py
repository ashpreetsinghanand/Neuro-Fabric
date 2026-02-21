from typing import Annotated, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class ColumnInfo(TypedDict):
    name: str
    data_type: str
    nullable: bool
    default: Any
    is_primary_key: bool
    is_foreign_key: bool
    foreign_key_ref: str | None  # "table.column" format


class TableSchema(TypedDict):
    table_name: str
    schema_name: str
    columns: list[ColumnInfo]
    primary_keys: list[str]
    foreign_keys: list[dict]   # [{column, ref_table, ref_column}]
    unique_constraints: list[list[str]]
    indexes: list[dict]
    row_count: int | None


class ColumnQuality(TypedDict):
    column_name: str
    null_count: int
    null_rate: float
    distinct_count: int
    min_value: Any
    max_value: Any
    mean_value: float | None
    std_dev: float | None


class TableQuality(TypedDict):
    table_name: str
    row_count: int
    column_quality: list[ColumnQuality]
    pk_uniqueness_rate: float | None
    freshness_column: str | None
    freshness_latest: str | None
    freshness_oldest: str | None
    overall_completeness: float


class TableDocumentation(TypedDict):
    table_name: str
    business_summary: str
    column_descriptions: dict[str, str]
    usage_recommendations: list[str]
    related_tables: list[str]
    suggested_queries: list[str]


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    db_config: dict                          # connection details supplied by user
    schema: dict[str, TableSchema]           # keyed by table_name
    quality_report: dict[str, TableQuality]  # keyed by table_name
    documentation: dict[str, TableDocumentation]  # keyed by table_name
    artifacts: list[str]                     # absolute paths of generated files
    current_task: str                        # active high-level task description
    errors: list[str]                        # accumulated error messages


def extract_message_content(content: Any) -> str:
    """
    Robustly extract text content from a LangChain message content object.
    Handles:
    1. Plain strings
    2. List of parts (dictionaries with a 'text' key) - common in Gemini 2.0+
    3. List of strings
    """
    if isinstance(content, str):
        return content
    
    if isinstance(content, list):
        if not content:
            return ""
        
        # Join all text parts if it's a list of dicts (Gemini style) or strings
        text_parts = []
        for part in content:
            if isinstance(part, str):
                text_parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                text_parts.append(part["text"])
            elif hasattr(part, "text"): # Some objects might have .text
                text_parts.append(part.text)
            else:
                text_parts.append(str(part))
        return "".join(text_parts)
    
    return str(content)
