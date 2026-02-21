"""
Neuro-Fabric FastAPI Server.

DuckDB-first architecture: local analytical engine with Supabase cloud fallback.
Exposes REST API endpoints for:
  - Database connection & schema browsing
  - SQL query execution (DuckDB)
  - LangGraph AI pipeline
  - Chat with data assistant
  - Artifact management
"""

from __future__ import annotations

import json
import logging
import traceback
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from core.config import LOG_LEVEL, OUTPUTS_DIR, validate_config

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("neuro-fabric-server")

# ── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Neuro-Fabric API",
    description="AI-Powered Enterprise Data Dictionary — Local-First with DuckDB",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global State ─────────────────────────────────────────────────────────────

pipeline_state: dict[str, Any] = {
    "schema": {},
    "quality_report": {},
    "documentation": {},
    "artifacts": [],
    "errors": [],
    "status": "idle",
    "progress": 0,
}

chat_thread_id = str(uuid.uuid4())


# ── Request / Response Models ────────────────────────────────────────────────

class ConnectRequest(BaseModel):
    url: str = ""
    name: str = "database"


class ChatRequest(BaseModel):
    message: str
    db_name: str = "database"


class PipelineRequest(BaseModel):
    url: str = ""
    name: str = "database"


class SQLRequest(BaseModel):
    query: str
    limit: int = 100


# ── Health / Connection ──────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    missing = validate_config()
    # Check DuckDB
    duckdb_ok = False
    try:
        from core.db_connectors import DUCKDB_PATH
        duckdb_ok = DUCKDB_PATH.exists()
    except Exception:
        pass

    return {
        "status": "ok",
        "config_valid": len(missing) == 0,
        "missing_keys": missing,
        "duckdb_available": duckdb_ok,
        "engine": "duckdb" if duckdb_ok else "postgres",
    }


@app.post("/api/connect")
async def connect_database(req: ConnectRequest):
    """Test database connection. Uses DuckDB by default."""
    try:
        from core.db_connectors import get_engine, test_connection as _test, get_db_type

        db_config = {"url": req.url, "name": req.name} if req.url else None
        engine = get_engine(db_config)
        ok = _test(engine)
        db_type = get_db_type(engine)
        return {
            "connected": ok,
            "engine": db_type,
            "message": f"Connected to {db_type}!" if ok else "Connection failed.",
        }
    except Exception as e:
        logger.error("Connection test failed: %s", e)
        return {"connected": False, "engine": "unknown", "message": str(e)}


# ── Schema Browser ───────────────────────────────────────────────────────────

@app.get("/api/schema")
async def get_schema():
    """Return database schema from DuckDB / Postgres."""
    if pipeline_state["schema"]:
        return pipeline_state["schema"]

    try:
        from core.db_connectors import get_engine, get_inspector, list_schemas

        engine = get_engine()
        inspector = get_inspector(engine)
        schemas = list_schemas(engine)

        schema_data = {}
        for schema_name in schemas:
            tables = inspector.get_table_names(schema=schema_name)
            for table_name in tables:
                full_name = f"{schema_name}.{table_name}" if schema_name != "main" else table_name
                columns = inspector.get_columns(table_name, schema=schema_name)
                pk = inspector.get_pk_constraint(table_name, schema=schema_name)
                fks = inspector.get_foreign_keys(table_name, schema=schema_name)

                # Get row count
                try:
                    with engine.connect() as conn:
                        qualified = f'"{schema_name}"."{table_name}"' if schema_name != "main" else f'"{table_name}"'
                        result = conn.execute(f"SELECT COUNT(*) FROM {qualified}")
                        if hasattr(result, 'fetchone'):
                            row_count = result.fetchone()[0]
                        else:
                            row_count = result.scalar()
                except Exception:
                    row_count = 0

                schema_data[full_name] = {
                    "table_name": table_name,
                    "schema": schema_name,
                    "columns": [
                        {
                            "name": col["name"],
                            "type": str(col.get("type", "unknown")),
                            "nullable": col.get("nullable", True),
                            "default": str(col.get("default", "")) if col.get("default") else None,
                            "is_primary_key": col["name"] in pk.get("constrained_columns", []),
                        }
                        for col in columns
                    ],
                    "primary_keys": pk.get("constrained_columns", []),
                    "foreign_keys": [
                        {
                            "from_column": fk["constrained_columns"][0] if fk.get("constrained_columns") else "",
                            "to_table": fk.get("referred_table", ""),
                            "to_column": fk["referred_columns"][0] if fk.get("referred_columns") else "",
                        }
                        for fk in fks
                    ],
                    "row_count": row_count,
                }

        pipeline_state["schema"] = schema_data
        return schema_data

    except Exception as e:
        logger.error("Schema extraction failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── SQL Query Engine ─────────────────────────────────────────────────────────

@app.post("/api/query")
async def execute_query(req: SQLRequest):
    """Execute a SQL query on DuckDB and return results."""
    try:
        from core.db_connectors import get_engine, get_db_type

        engine = get_engine()
        db_type = get_db_type(engine)

        # Security: block dangerous operations
        sql_upper = req.query.strip().upper()
        if any(kw in sql_upper for kw in ["DROP ", "TRUNCATE ", "ALTER ", "DELETE ", "INSERT ", "UPDATE "]):
            return {"error": "Write operations are disabled for safety.", "rows": [], "columns": []}

        with engine.connect() as conn:
            result = conn.execute(req.query)
            columns = result.keys() if hasattr(result, 'keys') else []
            rows = result.fetchmany(req.limit)

            # Convert to serializable format
            data_rows = []
            for row in rows:
                data_rows.append({col: _serialize_value(val) for col, val in zip(columns, row)})

        return {
            "columns": list(columns),
            "rows": data_rows,
            "row_count": len(data_rows),
            "engine": db_type,
            "truncated": len(data_rows) >= req.limit,
        }

    except Exception as e:
        logger.error("Query failed: %s", e)
        return {"error": str(e), "rows": [], "columns": []}


@app.get("/api/tables")
async def list_tables():
    """Quick endpoint listing all tables with row counts."""
    try:
        from core.db_connectors import get_engine, get_inspector, list_schemas

        engine = get_engine()
        inspector = get_inspector(engine)
        schemas = list_schemas(engine)

        tables = []
        for schema_name in schemas:
            for table_name in inspector.get_table_names(schema=schema_name):
                full_name = f"{schema_name}.{table_name}" if schema_name != "main" else table_name
                try:
                    with engine.connect() as conn:
                        qualified = f'"{schema_name}"."{table_name}"' if schema_name != "main" else f'"{table_name}"'
                        result = conn.execute(f"SELECT COUNT(*) FROM {qualified}")
                        row_count = result.fetchone()[0]
                except Exception:
                    row_count = 0

                col_count = len(inspector.get_columns(table_name, schema=schema_name))
                tables.append({
                    "name": full_name,
                    "schema": schema_name,
                    "table": table_name,
                    "rows": row_count,
                    "columns": col_count,
                })

        return {"tables": tables, "total": len(tables)}

    except Exception as e:
        logger.error("Table listing failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sample/{table}")
async def get_sample_rows(table: str, limit: int = 10):
    """Get sample rows from a table."""
    try:
        from core.db_connectors import get_engine

        engine = get_engine()

        # Handle schema-qualified names
        if "." in table:
            schema, tbl = table.split(".", 1)
            qualified = f'"{schema}"."{tbl}"'
        else:
            qualified = f'"{table}"'

        with engine.connect() as conn:
            result = conn.execute(f"SELECT * FROM {qualified} LIMIT {limit}")
            columns = result.keys()
            rows = result.fetchall()

        data = []
        for row in rows:
            data.append({col: _serialize_value(val) for col, val in zip(columns, row)})

        return {"columns": list(columns), "rows": data, "table": table}

    except Exception as e:
        logger.error("Sample failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Quality Metrics ──────────────────────────────────────────────────────────

@app.get("/api/quality")
async def get_quality():
    """Return data quality metrics — computed live from DuckDB."""
    if pipeline_state["quality_report"]:
        return pipeline_state["quality_report"]

    try:
        from core.db_connectors import get_engine, get_inspector, list_schemas

        engine = get_engine()
        inspector = get_inspector(engine)
        schemas = list_schemas(engine)

        quality = {}
        for schema_name in schemas:
            for table_name in inspector.get_table_names(schema=schema_name):
                full_name = f"{schema_name}.{table_name}" if schema_name != "main" else table_name
                columns = inspector.get_columns(table_name, schema=schema_name)

                qualified = f'"{schema_name}"."{table_name}"' if schema_name != "main" else f'"{table_name}"'

                with engine.connect() as conn:
                    total = conn.execute(f"SELECT COUNT(*) FROM {qualified}").fetchone()[0]
                    if total == 0:
                        continue

                    col_metrics = {}
                    for col_info in columns:
                        col_name = col_info["name"]
                        try:
                            null_count = conn.execute(
                                f'SELECT COUNT(*) FROM {qualified} WHERE "{col_name}" IS NULL'
                            ).fetchone()[0]

                            distinct_count = conn.execute(
                                f'SELECT COUNT(DISTINCT "{col_name}") FROM {qualified}'
                            ).fetchone()[0]

                            col_metrics[col_name] = {
                                "null_count": null_count,
                                "null_rate": round(null_count / total * 100, 2) if total > 0 else 0,
                                "distinct_count": distinct_count,
                                "completeness": round((1 - null_count / total) * 100, 2) if total > 0 else 100,
                            }
                        except Exception:
                            col_metrics[col_name] = {"null_count": 0, "null_rate": 0, "distinct_count": 0, "completeness": 100}

                    total_nulls = sum(m["null_count"] for m in col_metrics.values())
                    total_cells = total * len(columns) if columns else 1

                    quality[full_name] = {
                        "table_name": table_name,
                        "schema": schema_name,
                        "row_count": total,
                        "column_count": len(columns),
                        "completeness": round((1 - total_nulls / total_cells) * 100, 2) if total_cells > 0 else 100,
                        "columns": col_metrics,
                    }

        pipeline_state["quality_report"] = quality
        return quality

    except Exception as e:
        logger.error("Quality analysis failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── AI Documentation ─────────────────────────────────────────────────────────

@app.get("/api/docs")
async def get_docs():
    """Return AI-generated documentation."""
    return pipeline_state.get("documentation", {})


# ── Pipeline ─────────────────────────────────────────────────────────────────

@app.post("/api/pipeline")
async def run_pipeline(req: PipelineRequest):
    """Run the full AI documentation pipeline."""
    global pipeline_state

    pipeline_state["status"] = "running"
    pipeline_state["progress"] = 0
    pipeline_state["errors"] = []

    db_config = {"url": req.url, "name": req.name}

    try:
        from agents.supervisor import get_pipeline_app

        app_graph = get_pipeline_app()
        initial_state = {
            "messages": [],
            "db_config": db_config,
            "schema": {},
            "quality_report": {},
            "documentation": {},
            "artifacts": [],
            "current_task": "pipeline",
            "errors": [],
        }

        final_state = None
        for event in app_graph.stream(initial_state, stream_mode="values"):
            final_state = event

            schema_done = bool(event.get("schema"))
            quality_done = bool(event.get("quality_report"))
            docs_done = bool(event.get("documentation"))
            artifacts_done = bool(event.get("artifacts"))

            if artifacts_done:
                pipeline_state["progress"] = 100
            elif docs_done:
                pipeline_state["progress"] = 75
            elif quality_done:
                pipeline_state["progress"] = 50
            elif schema_done:
                pipeline_state["progress"] = 25

        if final_state:
            pipeline_state["schema"] = _serialize(final_state.get("schema", {}))
            pipeline_state["quality_report"] = _serialize(final_state.get("quality_report", {}))
            pipeline_state["documentation"] = _serialize(final_state.get("documentation", {}))
            pipeline_state["artifacts"] = final_state.get("artifacts", [])
            pipeline_state["errors"] = final_state.get("errors", [])
            pipeline_state["status"] = "complete"
            pipeline_state["progress"] = 100

        return {
            "status": "complete",
            "tables_extracted": len(pipeline_state["schema"]),
            "tables_quality": len(pipeline_state["quality_report"]),
            "tables_documented": len(pipeline_state["documentation"]),
            "artifacts_count": len(pipeline_state["artifacts"]),
            "errors": pipeline_state["errors"],
        }

    except Exception as e:
        logger.error("Pipeline failed: %s\n%s", e, traceback.format_exc())
        pipeline_state["status"] = "error"
        pipeline_state["errors"].append(str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/state")
async def get_state():
    """Return current pipeline state."""
    return {
        "status": pipeline_state["status"],
        "progress": pipeline_state["progress"],
        "schema": pipeline_state["schema"],
        "quality_report": pipeline_state["quality_report"],
        "documentation": pipeline_state["documentation"],
        "artifacts": pipeline_state["artifacts"],
        "errors": pipeline_state["errors"],
        "table_count": len(pipeline_state["schema"]),
    }


# ── Chat ─────────────────────────────────────────────────────────────────────

@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Chat with the data assistant. Works with or without LLM API keys."""
    global chat_thread_id

    # If no API key: provide SQL-powered responses
    from core.config import GOOGLE_API_KEY

    if not GOOGLE_API_KEY:
        return _smart_chat_fallback(req.message)

    try:
        from langchain_core.messages import HumanMessage
        from agents.supervisor import get_chat_app

        chat_app = get_chat_app()
        db_config = {"url": "", "name": req.db_name}

        chat_input = {
            "messages": [HumanMessage(content=req.message)],
            "db_config": db_config,
            "schema": pipeline_state.get("schema", {}),
            "quality_report": pipeline_state.get("quality_report", {}),
            "documentation": pipeline_state.get("documentation", {}),
            "artifacts": pipeline_state.get("artifacts", []),
            "current_task": "chat",
            "errors": [],
        }

        config = {"configurable": {"thread_id": chat_thread_id}}
        result = chat_app.invoke(chat_input, config=config)
        ai_messages = result.get("messages", [])
        response = ai_messages[-1].content if ai_messages else "I couldn't generate a response."

        return {"response": response}

    except Exception as e:
        logger.error("Chat failed: %s\n%s", e, traceback.format_exc())
        # Fallback to SQL-powered chat
        return _smart_chat_fallback(req.message)


def _smart_chat_fallback(message: str) -> dict[str, str]:
    """SQL-powered chat fallback when no LLM API key is available."""
    try:
        from core.db_connectors import get_engine

        engine = get_engine()
        msg_lower = message.lower()

        # Pattern match common queries
        if any(kw in msg_lower for kw in ["how many", "count", "total"]):
            if "customer" in msg_lower:
                with engine.connect() as conn:
                    count = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
                return {"response": f"📊 There are **{count:,}** customers in the database."}
            elif "order" in msg_lower:
                with engine.connect() as conn:
                    count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
                return {"response": f"📊 There are **{count:,}** orders in the database."}
            elif "product" in msg_lower:
                with engine.connect() as conn:
                    count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
                return {"response": f"📊 There are **{count:,}** products in the database."}
            elif "table" in msg_lower:
                with engine.connect() as conn:
                    result = conn.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema NOT IN ('information_schema','pg_catalog')")
                    count = result.fetchone()[0]
                return {"response": f"📊 There are **{count}** tables across all schemas."}

        if any(kw in msg_lower for kw in ["schema", "table", "list"]):
            with engine.connect() as conn:
                result = conn.execute("""
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_schema NOT IN ('information_schema','pg_catalog')
                    ORDER BY table_schema, table_name
                """)
                tables = result.fetchall()
            lines = ["📁 **Database Tables:**\n"]
            current_schema = None
            for row in tables:
                if row[0] != current_schema:
                    current_schema = row[0]
                    lines.append(f"\n**{current_schema}** schema:")
                lines.append(f"  • `{row[1]}`")
            return {"response": "\n".join(lines)}

        if any(kw in msg_lower for kw in ["revenue", "sales", "money"]):
            with engine.connect() as conn:
                result = conn.execute("""
                    SELECT
                        COUNT(DISTINCT o.order_id) AS orders,
                        ROUND(SUM(oi.price)::NUMERIC, 2) AS revenue,
                        ROUND(AVG(oi.price)::NUMERIC, 2) AS avg_price
                    FROM orders o JOIN order_items oi ON o.order_id = oi.order_id
                    WHERE o.order_status = 'delivered'
                """)
                row = result.fetchone()
            return {"response": f"💰 **Revenue Summary:**\n- Total delivered orders: **{row[0]:,}**\n- Total revenue: **R$ {row[1]:,.2f}**\n- Average item price: **R$ {row[2]:,.2f}**"}

        if any(kw in msg_lower for kw in ["quality", "null", "missing"]):
            with engine.connect() as conn:
                result = conn.execute("""
                    SELECT table_name, check_type, check_result, details
                    FROM staging.data_quality_log
                    ORDER BY checked_at DESC LIMIT 10
                """)
                rows = result.fetchall()
            lines = ["🔍 **Recent Quality Checks:**\n"]
            for row in rows:
                icon = "✅" if row[2] == "pass" else "⚠️" if row[2] == "warning" else "❌"
                lines.append(f"  {icon} `{row[0]}` → {row[1]}: {row[2]}")
            return {"response": "\n".join(lines)}

        if any(kw in msg_lower for kw in ["top", "best", "popular"]):
            with engine.connect() as conn:
                result = conn.execute("""
                    SELECT p.product_name, pc.category_name_english,
                           COUNT(*) AS orders, ROUND(SUM(oi.price)::NUMERIC, 2) AS revenue
                    FROM order_items oi
                    JOIN products p ON p.product_id = oi.product_id
                    JOIN product_categories pc ON pc.category_id = p.category_id
                    GROUP BY p.product_name, pc.category_name_english
                    ORDER BY orders DESC LIMIT 5
                """)
                rows = result.fetchall()
            lines = ["🏆 **Top 5 Products by Orders:**\n"]
            for i, row in enumerate(rows, 1):
                lines.append(f"  {i}. **{row[0]}** ({row[1]}) — {row[2]} orders, R$ {row[3]:,.2f}")
            return {"response": "\n".join(lines)}

        # Default: show help
        return {"response": (
            "🧠 **Neuro-Fabric Data Assistant** (SQL Mode)\n\n"
            "I can answer questions about your database! Try:\n"
            "- *\"How many customers?\"*\n"
            "- *\"List all tables\"*\n"
            "- *\"Show me revenue stats\"*\n"
            "- *\"Top products\"*\n"
            "- *\"Quality report\"*\n\n"
            "💡 For full AI-powered chat, add your `GOOGLE_API_KEY` to `.env`.\n"
            "You can also use the **SQL Query** tab to run any custom query!"
        )}

    except Exception as e:
        return {"response": f"Error: {str(e)}"}


@app.post("/api/chat/reset")
async def reset_chat():
    global chat_thread_id
    chat_thread_id = str(uuid.uuid4())
    return {"status": "ok", "thread_id": chat_thread_id}


# ── Artifacts ────────────────────────────────────────────────────────────────

@app.get("/api/artifacts")
async def get_artifacts():
    artifacts = []
    # Scan outputs dir
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    for p in sorted(OUTPUTS_DIR.glob("*.*")):
        artifacts.append({
            "path": str(p),
            "name": p.name,
            "size_kb": round(p.stat().st_size / 1024, 1),
            "type": p.suffix.lstrip("."),
        })
    return artifacts


@app.get("/api/artifacts/download/{filename}")
async def download_artifact(filename: str):
    path = OUTPUTS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(path, filename=filename)


# ── DuckDB Analytics ─────────────────────────────────────────────────────────

@app.get("/api/analytics/overview")
async def analytics_overview():
    """Quick analytics overview from DuckDB."""
    try:
        from core.db_connectors import get_engine

        engine = get_engine()
        with engine.connect() as conn:
            orders = conn.execute("SELECT COUNT(*), COUNT(DISTINCT customer_id) FROM orders").fetchone()
            revenue = conn.execute("SELECT COALESCE(SUM(price), 0), COALESCE(AVG(price), 0) FROM order_items").fetchone()
            products = conn.execute("SELECT COUNT(*) FROM products").fetchone()
            sellers = conn.execute("SELECT COUNT(*) FROM sellers").fetchone()
            reviews = conn.execute("SELECT COUNT(*), COALESCE(AVG(score), 0) FROM reviews").fetchone()
            status_dist = conn.execute("""
                SELECT order_status, COUNT(*) AS cnt
                FROM orders GROUP BY order_status ORDER BY cnt DESC
            """).fetchall()

        return {
            "total_orders": orders[0],
            "unique_customers": orders[1],
            "total_revenue": round(float(revenue[0]), 2),
            "avg_item_price": round(float(revenue[1]), 2),
            "total_products": products[0],
            "total_sellers": sellers[0],
            "total_reviews": reviews[0],
            "avg_review_score": round(float(reviews[1]), 2),
            "order_status": {row[0]: row[1] for row in status_dist},
        }

    except Exception as e:
        logger.error("Analytics overview failed: %s", e)
        return {"error": str(e)}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _serialize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(v) for v in obj]
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return str(obj)


def _serialize_value(val: Any) -> Any:
    """Serialize a single value for JSON response."""
    if val is None:
        return None
    if isinstance(val, (int, float, bool, str)):
        return val
    if isinstance(val, (bytes, bytearray)):
        return val.hex()
    from datetime import datetime, date
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, date):
        return val.isoformat()
    return str(val)


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print("🧠 Neuro-Fabric API Server")
    print("   http://localhost:8000")
    print("   http://localhost:8000/docs (Swagger UI)")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
