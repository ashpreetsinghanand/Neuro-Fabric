"""
Neuro-Fabric FastAPI Server — DuckDB-first architecture.
"""
from __future__ import annotations
import json, logging, traceback, uuid
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from core.config import LOG_LEVEL, OUTPUTS_DIR, validate_config

logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO),
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("neuro-fabric-server")

app = FastAPI(title="Neuro-Fabric API",
              description="AI-Powered Data Dictionary — Local-First DuckDB",
              version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

# ── State ────────────────────────────────────────────────────────────────────
pipeline_state: dict[str, Any] = {
    "schema": {}, "quality_report": {}, "documentation": {},
    "artifacts": [], "errors": [], "status": "idle", "progress": 0,
}
chat_thread_id = str(uuid.uuid4())

# Database configurations for hackathon datasets
DATABASE_CONFIGS = {
    "olist": {
        "name": "olist",
        "display_name": "Olist E-Commerce",
        "tables": ["orders", "customers", "products", "sellers", "order_items", "payments", "reviews", "geolocation", "product_category_name_translation"]
    },
    "bike_store": {
        "name": "bike_store", 
        "display_name": "Bike Store",
        "tables": ["stores", "staffs", "categories", "brands", "products", "customers", "orders", "order_items", "stocks"]
    },
    "chinook": {
        "name": "chinook",
        "display_name": "Chinook",
        "tables": ["artists", "albums", "tracks", "invoices", "invoice_items", "customers", "employees", "genres", "media_types", "playlists", "playlist_track"]
    }
}

# Current selected database
_current_engine: Any = None
_current_engine_type: str = "duckdb"  # 'duckdb', 'supabase', 'postgres', etc.

def _get_engine_forced(force_supabase: bool = False) -> Any:
    """Get database engine with option to force Supabase connection."""
    global _current_engine, _current_engine_type
    
    from core.db_connectors import get_engine, _build_supabase_url, create_engine, DuckDBEngine
    from core.config import SUPABASE_URL, SUPABASE_KEY, DATABASE_URL
    
    if force_supabase:
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                url = _build_supabase_url()
                _current_engine = create_engine(url, pool_pre_ping=True)
                _current_engine_type = "supabase"
                logger.info("Forced connection to Supabase")
                return _current_engine
            except Exception as e:
                logger.error(f"Failed to connect to Supabase: {e}")
                raise
        else:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env to use Supabase")
    
    # Default behavior
    _current_engine = get_engine()
    if isinstance(_current_engine, DuckDBEngine):
        _current_engine_type = "duckdb"
    else:
        _current_engine_type = "postgres"  # Could be Supabase or other PostgreSQL
    return _current_engine

@app.on_event("startup")
async def startup_event():
    """Auto-connect to database on startup if configured in .env"""
    from core.config import DATABASE_URL, SUPABASE_URL
    if DATABASE_URL or SUPABASE_URL:
        try:
            logger.info("Startup: Attempting auto-reconnect to database...")
            _get_engine_forced()
            logger.info("Startup: Auto-reconnect successful.")
        except Exception as e:
            logger.warning(f"Startup: Auto-reconnect failed (this is expected if .env isn't set up yet): {e}")

# ── Models ───────────────────────────────────────────────────────────────────
class ConnectRequest(BaseModel):
    db_url: str = ""
    db_type: str = "postgres"
    neo4j_uri: str = ""
    neo4j_user: str = ""
    neo4j_password: str = ""
    github_token: str = ""
    github_repo: str = ""

class ChatRequest(BaseModel):
    message: str
    db: str = "olist"
    history: list = []

class PipelineRequest(BaseModel):
    url: str = ""
    name: str = "database"

class SQLRequest(BaseModel):
    query: str
    limit: int = 100

@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "engine": _current_engine_type,
        "connected": _current_engine is not None
    }

# ── Database Selection ───────────────────────────────────────────────────────
@app.get("/api/databases")
async def list_databases():
    """List available databases"""
    return {"databases": list(DATABASE_CONFIGS.keys()), "current": _current_engine_type}

@app.post("/api/databases/{db_name}")
async def select_database(db_name: str):
    """Switch to a different database - now returns info about current connection"""
    global _current_engine_type
    if db_name in DATABASE_CONFIGS:
        # Reset pipeline state when switching
        pipeline_state["schema"] = {}
        pipeline_state["quality_report"] = {}
        pipeline_state["documentation"] = {}
        return {"success": True, "database": db_name, "engine": _current_engine_type}
    return {"success": False, "error": "Database not found"}

# ── Tables ───────────────────────────────────────────────────────────────────
@app.get("/api/tables")
async def list_tables_endpoint(db: str = ""):
    """Get list of tables dynamically from the connected database."""
    try:
        from core.db_connectors import get_inspector, list_schemas, DuckDBEngine
        from sqlalchemy import inspect as sa_inspect, text
        
        if not _current_engine:
            return {"tables": [], "total": 0, "error": "Connect to database first"}
            
        engine = _current_engine
        inspector = get_inspector(engine)
        tables = []
        
        # Dynamically discover all schemas and tables
        schemas = list_schemas(engine)
        for schema_name in schemas:
            try:
                table_names = inspector.get_table_names(schema=schema_name)
                for table_name in table_names:
                    try:
                        # Get column count
                        cols = inspector.get_columns(table_name, schema=schema_name)
                        
                        # Get row count
                        with engine.connect() as conn:
                            if isinstance(engine, DuckDBEngine):
                                q = f'"{schema_name}"."{table_name}"' if schema_name != "main" else f'"{table_name}"'
                                rc = conn.execute(f"SELECT COUNT(*) FROM {q}").fetchone()[0]
                            else:
                                q = f'"{schema_name}"."{table_name}"'
                                rc = conn.execute(text(f"SELECT COUNT(*) FROM {q}")).fetchone()[0]
                        
                        tables.append({
                            "table_name": table_name,
                            "schema_name": schema_name,
                            "row_count": rc,
                            "column_count": len(cols)
                        })
                    except Exception as e:
                        logger.warning(f"Failed to get info for {schema_name}.{table_name}: {e}")
                        tables.append({
                            "table_name": table_name,
                            "schema_name": schema_name,
                            "row_count": 0,
                            "column_count": 0
                        })
            except Exception as e:
                logger.warning(f"Failed to list tables for schema {schema_name}: {e}")
        
        return {"tables": tables, "total": len(tables)}
    except Exception as e:
        logger.error("Tables endpoint failed: %s", e)
        return {"tables": [], "total": 0, "error": str(e)}

# ── Columns ──────────────────────────────────────────────────────────────────
@app.get("/api/columns")
async def get_columns_endpoint(table: str = "", schema: str = ""):
    """Get columns for a specific table dynamically."""
    if not table:
        return {"error": "Table name is required", "columns": []}
    
    try:
        from core.db_connectors import get_inspector, DuckDBEngine
        from sqlalchemy import inspect as sa_inspect, text
        
        if not _current_engine:
            return {"error": "Connect to database first", "columns": []}
            
        engine = _current_engine
        inspector = get_inspector(engine)
        
        # Use provided schema or default to 'main' for DuckDB
        schema_name = schema or ("main" if isinstance(engine, DuckDBEngine) else "public")
        
        try:
            cols = inspector.get_columns(table, schema=schema_name)
            
            # Try to get primary key info
            try:
                pk_constraint = inspector.get_pk_constraint(table, schema=schema_name)
                pk_cols = set(pk_constraint.get("constrained_columns", []))
            except:
                pk_cols = set()
            
            columns = [{
                "column_name": c["name"],
                "data_type": str(c.get("type", "?")),
                "is_nullable": c.get("nullable", True),
                "is_primary_key": c["name"] in pk_cols
            } for c in cols]
            
            return {"table": table, "schema": schema_name, "columns": columns}
        except Exception as e:
            logger.error(f"Failed to get columns for {schema_name}.{table}: {e}")
            return {"error": str(e), "columns": []}
            
    except Exception as e:
        logger.error("Columns endpoint failed: %s", e)
        return {"error": str(e), "columns": []}

# ── Quality Metrics ─────────────────────────────────────────────────────────
@app.get("/api/quality")
async def get_quality_endpoint(table: str = "", schema: str = ""):
    """Get quality metrics dynamically for all tables or a specific table."""
    try:
        from core.db_connectors import get_inspector, list_schemas, DuckDBEngine
        from sqlalchemy import text
        
        if not _current_engine:
            return {"error": "Connect to database first"}
            
        engine = _current_engine
        inspector = get_inspector(engine)
        
        results = []
        
        # Get list of tables to analyze
        if table:
            # Single table analysis
            schema_name = schema or ("main" if isinstance(engine, DuckDBEngine) else "public")
            tables_to_analyze = [(schema_name, table)]
        else:
            # Analyze all tables across all schemas
            tables_to_analyze = []
            for sn in list_schemas(engine):
                try:
                    table_names = inspector.get_table_names(schema=sn)
                    for tn in table_names:
                        tables_to_analyze.append((sn, tn))
                except Exception as e:
                    logger.warning(f"Failed to list tables for schema {sn}: {e}")
        
        for schema_name, table_name in tables_to_analyze:
            try:
                with engine.connect() as conn:
                    # Get row count
                    if isinstance(engine, DuckDBEngine):
                        q = f'"{schema_name}"."{table_name}"' if schema_name != "main" else f'"{table_name}"'
                        total_result = conn.execute(f"SELECT COUNT(*) FROM {q}")
                    else:
                        q = f'"{schema_name}"."{table_name}"'
                        total_result = conn.execute(text(f"SELECT COUNT(*) FROM {q}"))
                    
                    total = total_result.fetchone()[0]
                    if total == 0:
                        continue
                    
                    # Get columns
                    cols = inspector.get_columns(table_name, schema=schema_name)
                    
                    column_quality = []
                    for col in cols:
                        col_name = col["name"]
                        try:
                            if isinstance(engine, DuckDBEngine):
                                null_result = conn.execute(f'SELECT COUNT(*) FROM {q} WHERE "{col_name}" IS NULL').fetchone()
                                distinct_result = conn.execute(f'SELECT COUNT(DISTINCT "{col_name}") FROM {q}').fetchone()
                            else:
                                null_result = conn.execute(text(f'SELECT COUNT(*) FROM {q} WHERE "{col_name}" IS NULL')).fetchone()
                                distinct_result = conn.execute(text(f'SELECT COUNT(DISTINCT "{col_name}") FROM {q}')).fetchone()
                            
                            null_count = null_result[0] if null_result else 0
                            distinct_count = distinct_result[0] if distinct_result else 0
                            
                            column_quality.append({
                                "column_name": col_name,
                                "null_rate": round(null_count / total, 4) if total > 0 else 0,
                                "distinct_count": distinct_count
                            })
                        except Exception as col_e:
                            logger.warning(f"Quality check failed for column {col_name}: {col_e}")
                            column_quality.append({
                                "column_name": col_name,
                                "null_rate": 0,
                                "distinct_count": 0
                            })
                    
                    results.append({
                        "table_name": table_name,
                        "schema_name": schema_name,
                        "row_count": total,
                        "overall_completeness": round(1 - (sum(c["null_rate"] for c in column_quality) / len(column_quality)), 4) if column_quality else 1,
                        "column_quality": column_quality
                    })
            except Exception as e:
                logger.warning(f"Quality check failed for {schema_name}.{table_name}: {e}")
                continue
        
        return {"quality": results, "total": len(results)}
    except Exception as e:
        logger.error("Quality endpoint failed: %s", e)
        return {"quality": [], "total": 0, "error": str(e)}

# ── Documentation ───────────────────────────────────────────────────────────
@app.get("/api/docs")
async def get_docs(db: str = "olist", table: str = ""):
    """Get AI-generated documentation"""
    docs = pipeline_state.get("documentation", {})
    
    if table:
        return [docs.get(table, {"table_name": table, "business_summary": "No documentation yet", "column_descriptions": {}, "usage_recommendations": []})]
    
    return [v for k, v in docs.items()]

@app.post("/api/generate-docs")
async def generate_docs(table: str = "", schema: str = ""):
    """Generate AI documentation for tables dynamically discovered from the database."""
    global pipeline_state
    
    try:
        from core.db_connectors import get_engine, get_inspector, list_schemas, DuckDBEngine
        from core.config import GOOGLE_API_KEY
        from sqlalchemy import text
        
        engine = get_engine()
        inspector = get_inspector(engine)
        
        docs = {}
        
        # Dynamically discover tables to document
        tables_to_document = []
        if table:
            # Single table documentation
            schema_name = schema or ("main" if isinstance(engine, DuckDBEngine) else "public")
            tables_to_document = [(schema_name, table)]
        else:
            # Document all tables across all schemas
            for sn in list_schemas(engine):
                try:
                    table_names = inspector.get_table_names(schema=sn)
                    for tn in table_names:
                        tables_to_document.append((sn, tn))
                except Exception as e:
                    logger.warning(f"Failed to list tables for schema {sn}: {e}")
        
        for schema_name, table_name in tables_to_document:
            try:
                # Get table info
                with engine.connect() as conn:
                    cols = inspector.get_columns(table_name, schema=schema_name)
                    
                    if isinstance(engine, DuckDBEngine):
                        q = f'"{schema_name}"."{table_name}"' if schema_name != "main" else f'"{table_name}"'
                        total = conn.execute(f"SELECT COUNT(*) FROM {q}").fetchone()[0]
                    else:
                        q = f'"{schema_name}"."{table_name}"'
                        total = conn.execute(text(f"SELECT COUNT(*) FROM {q}")).fetchone()[0]
                
                # Build column info
                columns_info = "\n".join([f"- {c['name']}: {c.get('type', '?')}" for c in cols]) if cols else "No columns"
                
                if GOOGLE_API_KEY:
                    # Use Gemini to generate docs
                    prompt = f"""Generate a business-friendly data dictionary entry for table '{table_name}' (schema: '{schema_name}').

Table: {table_name}
Schema: {schema_name}
Row Count: {total}
Columns:
{columns_info}

Provide:
1. A 2-3 sentence business summary explaining what this table contains
2. Column descriptions (brief, business-friendly) as a JSON object
3. Usage recommendations (2-3 bullet points) as a JSON array

Format as JSON with keys: business_summary, column_descriptions (object), usage_recommendations (array)"""
                    
                    # Simple Gemini call
                    import google.genai as genai
                    genai_client = genai.Client(api_key=GOOGLE_API_KEY)
                    response = genai_client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt
                    )
                    
                    try:
                        import json
                        # Try to parse JSON from response (strip markdown blocks if present)
                        content = response.text
                        if not isinstance(content, str):
                            # Handle Gemini 2.0 list responses
                            content = content[0] if isinstance(content, list) else str(content)
                            
                        clean_text = content.replace('```json', '').replace('```', '').strip()
                        doc_data = json.loads(clean_text)
                        full_name = f"{schema_name}.{table_name}" if schema_name != "main" else table_name
                        docs[full_name] = {
                            "table_name": table_name,
                            "schema_name": schema_name,
                            "business_summary": doc_data.get("business_summary", ""),
                            "column_descriptions": doc_data.get("column_descriptions", {}),
                            "usage_recommendations": doc_data.get("usage_recommendations", [])
                        }
                    except Exception as parse_e:
                        logger.warning(f"Failed to parse Gemini JSON: {parse_e}")
                        # If not valid JSON, store as text
                        full_name = f"{schema_name}.{table_name}" if schema_name != "main" else table_name
                        docs[full_name] = {
                            "table_name": table_name,
                            "schema_name": schema_name,
                            "business_summary": response.text[:500] if response.text else f"Table {table_name} with {total} rows",
                            "column_descriptions": {},
                            "usage_recommendations": []
                        }
                else:
                    # Fallback: Generate basic docs
                    full_name = f"{schema_name}.{table_name}" if schema_name != "main" else table_name
                    docs[full_name] = {
                        "table_name": table_name,
                        "schema_name": schema_name,
                        "business_summary": f"This table contains {total} records for {table_name}.",
                        "column_descriptions": {c['name']: str(c.get('type', '?')) for c in cols} if cols else {},
                        "usage_recommendations": ["Join with related tables using foreign keys", "Check data quality metrics before analysis"]
                    }
            except Exception as e:
                logger.warning(f"Doc generation failed for {schema_name}.{table_name}: {e}")
                full_name = f"{schema_name}.{table_name}" if schema_name != "main" else table_name
                docs[full_name] = {
                    "table_name": table_name,
                    "schema_name": schema_name,
                    "business_summary": f"Table {table_name} (error generating docs: {str(e)[:100]})",
                    "column_descriptions": {},
                    "usage_recommendations": []
                }
        
        pipeline_state["documentation"] = docs
        return {"success": True, "tables": len(docs)}
    except Exception as e:
        logger.error("Generate docs failed: %s", e)
        return {"success": False, "error": str(e)}

@app.post("/api/settings/connect")
async def settings_connect(req: ConnectRequest):
    """Dynamic connection endpoint for SaaS model."""
    global _current_engine, _current_engine_type
    try:
        from sqlalchemy import create_engine
        from core.db_connectors import test_connection, get_db_type, DuckDBEngine
        import os
        
        ok = False
        db_type = "none"
        message = "Settings updated."

        # Update environment variables for dynamic connectors
        if req.neo4j_uri: os.environ["NEO4J_URI"] = req.neo4j_uri
        if req.neo4j_user: os.environ["NEO4J_USER"] = req.neo4j_user
        if req.neo4j_password: os.environ["NEO4J_PASSWORD"] = req.neo4j_password
        if req.github_token: os.environ["GITHUB_TOKEN"] = req.github_token
        if req.github_repo: os.environ["GITHUB_REPO"] = req.github_repo

        # Force reload Neo4j driver
        import core.neo4j_connector as neo4j_conn
        neo4j_conn._driver = None  # Reset driver singleton

        if req.db_url:
            if req.db_url.startswith("duckdb"):
                from core.db_connectors import DuckDBEngine
                path = req.db_url.split("///")[-1] if "///" in req.db_url else req.db_url
                _current_engine = DuckDBEngine(path)
            else:
                _current_engine = create_engine(req.db_url, pool_pre_ping=True)
            
            ok = test_connection(_current_engine)
            db_type = "duckdb" if isinstance(_current_engine, DuckDBEngine) else get_db_type(_current_engine)
            _current_engine_type = db_type
            message = "Connected successfully!" if ok else "Database connection failed."
            
            # Reset pipeline state on new connection
            pipeline_state["schema"] = {}
            pipeline_state["quality_report"] = {}
            pipeline_state["documentation"] = {}
        else:
            # If no DB URL is provided, disconnect
            _current_engine = None
            _current_engine_type = "none"
            ok = False
            message = "Database disconnected. Other settings saved."

        return {"connected": ok, "engine": db_type, "message": message}
    except Exception as e:
        logger.error("Connect failed: %s", e)
        return {"connected": False, "engine": "error", "message": str(e)}

# ── Schema ───────────────────────────────────────────────────────────────────
@app.get("/api/schema")
async def get_schema():
    if pipeline_state["schema"]:
        return pipeline_state["schema"]
    try:
        from core.db_connectors import get_inspector, list_schemas, DuckDBEngine
        from sqlalchemy import text
        
        if not _current_engine:
            return {"success": False, "error": "Connect to database first"}
            
        engine = _current_engine
        inspector = get_inspector(engine)
        schemas = list_schemas(engine)
        data = {}
        
        for sn in schemas:
            try:
                table_names = inspector.get_table_names(schema=sn)
            except Exception as e:
                logger.warning(f"Could not get tables for schema {sn}: {e}")
                continue
                
            for tn in table_names:
                full = f"{sn}.{tn}" if sn != "main" and sn != "public" else tn
                
                try:
                    cols = inspector.get_columns(tn, schema=sn)
                except Exception:
                    cols = []
                    
                try:
                    pk = inspector.get_pk_constraint(tn, schema=sn)
                    pk_cols = pk.get("constrained_columns", []) if pk else []
                except Exception:
                    pk_cols = []
                    
                try:
                    fks = inspector.get_foreign_keys(tn, schema=sn)
                except Exception:
                    fks = []
                    
                rc = 0
                try:
                    with engine.connect() as conn:
                        if isinstance(engine, DuckDBEngine):
                            q = f'"{sn}"."{tn}"' if sn != "main" else f'"{tn}"'
                            rc = conn.execute(f"SELECT COUNT(*) FROM {q}").fetchone()[0]
                        else:
                            # Postgres/Supabase quoting
                            q = f'"{sn}"."{tn}"'
                            rc = conn.execute(text(f"SELECT COUNT(*) FROM {q}")).fetchone()[0]
                except Exception as e:
                    logger.warning(f"Row count failed for {full}: {e}")
                    
                formatted_cols = []
                for c in cols:
                    formatted_cols.append({
                        "name": c.get("name", ""),
                        "type": str(c.get("type", "?")),
                        "nullable": c.get("nullable", True),
                        "is_primary_key": c.get("name") in pk_cols
                    })
                    
                formatted_fks = []
                for f in fks:
                    local_cols = f.get("constrained_columns", [])
                    remote_cols = f.get("referred_columns", [])
                    formatted_fks.append({
                        "from_column": local_cols[0] if local_cols else "",
                        "to_table": f.get("referred_table", ""),
                        "to_column": remote_cols[0] if remote_cols else ""
                    })

                data[full] = {
                    "table_name": tn,
                    "schema": sn,
                    "row_count": rc,
                    "columns": formatted_cols,
                    "primary_keys": pk_cols,
                    "foreign_keys": formatted_fks
                }
                
        pipeline_state["schema"] = data
        return data
    except Exception as e:
        logger.error("Schema failed: %s", e)
        return {"success": False, "error": str(e)}

# ── SQL Query ────────────────────────────────────────────────────────────────
@app.post("/api/query")
async def execute_query(req: SQLRequest):
    try:
        from core.db_connectors import get_db_type
        
        if not _current_engine:
            return {"error": "Connect to database first"}
            
        engine = _current_engine
        sql_up = req.query.strip().upper()
        if any(k in sql_up for k in ["DROP ", "TRUNCATE ", "ALTER ", "DELETE ", "INSERT ", "UPDATE "]):
            return {"error": "Write operations disabled.", "rows": [], "columns": []}
        with engine.connect() as conn:
            result = conn.execute(req.query)
            columns = result.keys() if hasattr(result, 'keys') else []
            rows = result.fetchmany(req.limit)
            data = [{c: _ser_val(v) for c, v in zip(columns, r)} for r in rows]
        return {"columns": list(columns), "rows": data, "row_count": len(data),
                "engine": get_db_type(engine), "truncated": len(data) >= req.limit}
    except Exception as e:
        logger.error("Query failed: %s", e)
        return {"error": str(e), "rows": [], "columns": []}

@app.get("/api/sample/{table}")
async def get_sample_rows(table: str, limit: int = 10):
    try:
        from core.db_connectors import DuckDBEngine
        from sqlalchemy import text
        
        if not _current_engine:
            return {"success": False, "error": "Connect to database first"}
            
        engine = _current_engine
        if "." in table:
            s, t = table.split(".", 1)
            # Ensure safe quoting
            q = f'"{s}"."{t}"'
        else:
            q = f'"{table}"'
            
        with engine.connect() as conn:
            if isinstance(engine, DuckDBEngine):
                result = conn.execute(f"SELECT * FROM {q} LIMIT {limit}")
            else:
                result = conn.execute(text(f"SELECT * FROM {q} LIMIT {limit}"))
                
            cols = result.keys()
            rows = result.fetchall()
            
        data = [{c: _ser_val(v) for c, v in zip(cols, r)} for r in rows]
        return {"columns": list(cols), "rows": data, "table": table}
    except Exception as e:
        logger.error("Sample failed: %s", e)
        raise HTTPException(500, str(e))

# ── Docs / Pipeline / State ──────────────────────────────────────────────────
@app.get("/api/docs")
async def get_docs():
    return pipeline_state.get("documentation", {})

class DocsGenerateRequest(BaseModel):
    table_name: str
    columns: list = []
    row_count: int = 0
    foreign_keys: list = []

@app.post("/api/docs/generate")
async def generate_docs(req: DocsGenerateRequest):
    """Generate AI-enhanced documentation for a specific table."""
    try:
        from core.config import GOOGLE_API_KEY
        if GOOGLE_API_KEY:
            # Use AI to generate enhanced documentation
            from langchain_core.messages import HumanMessage
            from agents.supervisor import get_chat_app
            chat_app = get_chat_app()
            
            prompt = f"""Generate comprehensive documentation for the database table '{req.table_name}':

Table: {req.table_name}
Row Count: {req.row_count:,}
Columns: {len(req.columns)}
Foreign Keys: {len(req.foreign_keys)}

Column Details:
{chr(10).join(f"- {c.get('name', 'unknown')}: {c.get('type', 'unknown')} ({'nullable' if c.get('nullable', True) else 'required'})" for c in req.columns[:20])}

Please provide:
1. A business-friendly description of what this table stores
2. Column descriptions with business context
3. Data quality notes
4. Suggested queries for analysis

Format as JSON with keys: table_name, business_description, column_descriptions (array), data_quality_notes (array), suggested_queries (array), business_insights (array)"""

            inp = {"messages": [HumanMessage(content=prompt)],
                   "db_config": {"url": "", "name": "database"},
                   "schema": {}, "quality_report": {}, "documentation": {},
                   "artifacts": [], "current_task": "chat", "errors": []}
            result = chat_app.invoke(inp, config={"configurable": {"thread_id": str(uuid.uuid4())}})
            msgs = result.get("messages", [])
            if msgs:
                import json
                try:
                    # Try to parse as JSON
                    content = msgs[-1].content
                    if not isinstance(content, str):
                        # Content might be a list (e.g. for multi-modal or tool use in new LangGraph)
                        content = content[0] if isinstance(content, list) else str(content)
                        
                    if '```json' in content:
                        content = content.split('```json')[1].split('```')[0]
                    return json.loads(content.strip())
                except:
                    pass
        
        # Fallback: Generate local documentation
        return _generate_local_docs(req)
    except Exception as e:
        logger.error("Docs generate failed: %s", e)
        return _generate_local_docs(req)

def _generate_local_docs(req: DocsGenerateRequest) -> dict:
    """Generate documentation locally without AI."""
    table_descriptions = {
        'customers': 'Stores customer information including unique identifiers, contact details, and location data.',
        'orders': 'Contains order transactions with status tracking, timestamps for purchase, approval, and delivery.',
        'order_items': 'Individual items within each order, tracking product, seller, price, and shipping costs.',
        'products': 'Product catalog with category classifications and physical dimensions.',
        'sellers': 'Seller profiles with location information for marketplace vendors.',
        'payments': 'Payment transactions linked to orders, tracking payment type, installments, and amounts.',
        'reviews': 'Customer reviews and satisfaction scores for completed orders.',
        'geolocation': 'Geographic coordinate mapping for Brazilian zip codes.',
        'product_categories': 'Product taxonomy with English translations of category names.'
    }
    
    column_descriptions = []
    for col in req.columns:
        name = col.get('name', '').lower()
        desc = 'Data field'
        if '_id' in name: desc = 'Unique identifier field'
        elif '_date' in name or 'timestamp' in name: desc = 'Temporal tracking field'
        elif 'name' in name: desc = 'Descriptive name field'
        elif 'count' in name or 'qty' in name: desc = 'Quantity counter'
        elif 'price' in name or 'value' in name or 'amount' in name: desc = 'Monetary value field'
        elif 'zip' in name or 'postal' in name: desc = 'Location identifier'
        elif 'city' in name or 'state' in name: desc = 'Geographic location field'
        elif 'status' in name: desc = 'Status indicator field'
        elif col.get('is_primary_key'): desc = 'Primary key - unique row identifier'
        
        business_use = 'General data field'
        if 'price' in name or 'value' in name: business_use = 'Revenue analytics'
        elif 'date' in name or 'timestamp' in name: business_use = 'Trend analysis, SLA monitoring'
        elif 'status' in name: business_use = 'Operational dashboards'
        elif 'customer' in name: business_use = 'Customer analytics, segmentation'
        elif 'product' in name: business_use = 'Inventory management, catalog'
        elif 'seller' in name: business_use = 'Vendor performance analysis'
        elif 'review' in name or 'score' in name: business_use = 'Customer satisfaction metrics'
        
        column_descriptions.append({
            'name': col.get('name', ''),
            'type': col.get('type', ''),
            'nullable': col.get('nullable', True),
            'is_pk': col.get('is_primary_key', False),
            'description': desc,
            'business_use': business_use
        })
    
    insights = []
    if req.foreign_keys:
        insights.append(f"**Relationships:** Connects to {', '.join(fk.get('to_table', '') for fk in req.foreign_keys)}")
    if any('timestamp' in c.get('name', '').lower() or 'date' in c.get('name', '').lower() for c in req.columns):
        insights.append("**Time-series:** Contains temporal data suitable for trend analysis")
    if any('price' in c.get('name', '').lower() or 'value' in c.get('name', '').lower() for c in req.columns):
        insights.append("**Financial:** Contains monetary values - ensure proper decimal handling")
    if req.row_count > 10000:
        insights.append(f"**Scale:** Large dataset ({req.row_count:,} rows) - consider partitioning")
    
    quality_notes = []
    nullable_cols = [c for c in req.columns if c.get('nullable', True)]
    if nullable_cols:
        quality_notes.append(f"{len(nullable_cols)} columns allow NULL values - check for missing data")
    if not any(c.get('is_primary_key') for c in req.columns):
        quality_notes.append("No primary key defined - verify data uniqueness")
    if req.row_count == 0:
        quality_notes.append("Empty table - verify data load completed")
    
    queries = {
        'customers': ['SELECT city, COUNT(*) as customer_count FROM customers GROUP BY city ORDER BY customer_count DESC LIMIT 10'],
        'orders': ['SELECT order_status, COUNT(*) FROM orders GROUP BY order_status'],
        'order_items': ['SELECT product_id, COUNT(*) as times_ordered, SUM(price) as total_revenue FROM order_items GROUP BY product_id ORDER BY total_revenue DESC LIMIT 10'],
        'payments': ['SELECT payment_type, COUNT(*), AVG(payment_value) FROM payments GROUP BY payment_type'],
        'reviews': ['SELECT review_score, COUNT(*) FROM reviews GROUP BY review_score ORDER BY review_score']
    }
    
    return {
        'table_name': req.table_name,
        'business_description': table_descriptions.get(req.table_name, f"Data table with {len(req.columns)} columns and {req.row_count:,} records."),
        'column_descriptions': column_descriptions,
        'data_quality_notes': quality_notes,
        'business_insights': insights,
        'suggested_queries': queries.get(req.table_name, [f'SELECT * FROM {req.table_name} LIMIT 10', f'SELECT COUNT(*) FROM {req.table_name}']),
        'generated_at': __import__('datetime').datetime.now().isoformat()
    }

@app.post("/api/pipeline")
async def run_pipeline(req: PipelineRequest):
    global pipeline_state
    pipeline_state["status"] = "running"; pipeline_state["progress"] = 0
    try:
        from agents.supervisor import get_pipeline_app
        graph = get_pipeline_app()
        state_in = {"messages": [], "db_config": {"url": req.url, "name": req.name},
                     "schema": {}, "quality_report": {}, "documentation": {},
                     "artifacts": [], "current_task": "pipeline", "errors": []}
        final = None
        for event in graph.stream(state_in, stream_mode="values"):
            final = event
            if event.get("artifacts"): pipeline_state["progress"] = 100
            elif event.get("documentation"): pipeline_state["progress"] = 75
            elif event.get("quality_report"): pipeline_state["progress"] = 50
            elif event.get("schema"): pipeline_state["progress"] = 25
        if final:
            for k in ["schema","quality_report","documentation","artifacts","errors"]:
                pipeline_state[k] = _ser(final.get(k, {} if k != "artifacts" and k != "errors" else []))
            pipeline_state["status"] = "complete"; pipeline_state["progress"] = 100
        return {"status": "complete", "tables": len(pipeline_state["schema"])}
    except Exception as e:
        logger.error("Pipeline failed: %s", e); pipeline_state["status"] = "error"
        raise HTTPException(500, str(e))

@app.get("/api/state")
async def get_state():
    return {k: pipeline_state[k] for k in pipeline_state}

# ── Chat ─────────────────────────────────────────────────────────────────────
@app.post("/api/chat")
async def chat(req: ChatRequest):
    global chat_thread_id
    from core.config import GOOGLE_API_KEY
    
    if not GOOGLE_API_KEY:
        return _smart_chat(req.message)
    try:
        from langchain_core.messages import HumanMessage
        from agents.supervisor import get_chat_app
        chat_app = get_chat_app()
        inp = {"messages": [HumanMessage(content=req.message)],
               "db_config": {"url": "", "name": "database"},
               "schema": pipeline_state.get("schema", {}),
               "quality_report": pipeline_state.get("quality_report", {}),
               "documentation": pipeline_state.get("documentation", {}),
               "artifacts": [], "current_task": "chat", "errors": []}
        result = chat_app.invoke(inp, config={"configurable": {"thread_id": chat_thread_id}})
        msgs = result.get("messages", [])
        if not msgs:
            return {"response": "No response."}
            
        content = msgs[-1].content
        if not isinstance(content, str):
            # Handle Gemini 2.0 list responses
            content = content[0] if isinstance(content, list) else str(content)
            
        return {"response": content}
    except Exception as e:
        logger.error("Chat LLM failed: %s", e)
        return _smart_chat(req.message)

def _smart_chat(msg: str, db_name: str = "") -> dict:
    """Smart chat responses using dynamically discovered database schema."""
    try:
        from core.db_connectors import get_inspector, list_schemas, DuckDBEngine
        from sqlalchemy import text
        
        if not _current_engine:
            return {"response": "⚠️ No database connected. Please connect a database in Settings first."}
            
        engine = _current_engine
        inspector = get_inspector(engine)
        ml = msg.lower()
        
        # Dynamically get all tables
        all_tables = []
        for sn in list_schemas(engine):
            try:
                tables = inspector.get_table_names(schema=sn)
                for tn in tables:
                    all_tables.append((sn, tn))
            except Exception as e:
                logger.warning(f"Failed to list tables for schema {sn}: {e}")
        
        if any(k in ml for k in ["how many", "count", "total"]):
            # Check if user is asking about a specific table
            for schema_name, table_name in all_tables:
                if table_name.lower() in ml:
                    with engine.connect() as c:
                        if isinstance(engine, DuckDBEngine):
                            q = f'"{schema_name}"."{table_name}"' if schema_name != "main" else f'"{table_name}"'
                            n = c.execute(f"SELECT COUNT(*) FROM {q}").fetchone()[0]
                        else:
                            q = f'"{schema_name}"."{table_name}"'
                            n = c.execute(text(f"SELECT COUNT(*) FROM {q}")).fetchone()[0]
                    return {"response": f"📊 There are **{n:,}** rows in the `{table_name}` table."}
            # List available tables
            table_list = [tn for _, tn in all_tables[:10]]
            return {"response": f"📊 Available tables: {', '.join(table_list)}{'...' if len(all_tables) > 10 else ''}\n\nTry: *How many [table_name]?*"}
        
        if any(k in ml for k in ["schema","table","list", "tables"]):
            table_list = [f"`{sn}.{tn}`" if sn != "main" else f"`{tn}`" for sn, tn in all_tables[:20]]
            lines = [f"📁 **Database Tables ({len(all_tables)} total):**\n"]
            lines.extend([f"  • {t}" for t in table_list])
            if len(all_tables) > 20:
                lines.append(f"  ... and {len(all_tables) - 20} more tables")
            return {"response": "\n".join(lines)}
        
        if any(k in ml for k in ["revenue","sales","money", "price", "amount"]):
            # Try common revenue tables by name matching
            revenue_keywords = ["order", "item", "payment", "sale", "transaction", "revenue"]
            for schema_name, table_name in all_tables:
                if any(kw in table_name.lower() for kw in revenue_keywords):
                    with engine.connect() as c:
                        try:
                            if isinstance(engine, DuckDBEngine):
                                q = f'"{schema_name}"."{table_name}"' if schema_name != "main" else f'"{table_name}"'
                                # Try to find price/value columns
                                cols = inspector.get_columns(table_name, schema=schema_name)
                                price_col = None
                                for col in cols:
                                    col_name = col['name'].lower()
                                    if 'price' in col_name or 'value' in col_name or 'amount' in col_name:
                                        price_col = col['name']
                                        break
                                
                                if price_col:
                                    r = c.execute(f"SELECT COUNT(*), COALESCE(SUM(\"{price_col}\"),0), COALESCE(AVG(\"{price_col}\"),0) FROM {q}").fetchone()
                                    return {"response": f"💰 **{table_name}**\n- {r[0]:,} records\n- Total: {r[1]:,.2f}\n- Average: {r[2]:,.2f}"}
                            else:
                                q = f'"{schema_name}"."{table_name}"'
                                cols = inspector.get_columns(table_name, schema=schema_name)
                                price_col = None
                                for col in cols:
                                    col_name = col['name'].lower()
                                    if 'price' in col_name or 'value' in col_name or 'amount' in col_name:
                                        price_col = col['name']
                                        break
                                
                                if price_col:
                                    r = c.execute(text(f"SELECT COUNT(*), COALESCE(SUM(\"{price_col}\"),0), COALESCE(AVG(\"{price_col}\"),0) FROM {q}")).fetchone()
                                    return {"response": f"💰 **{table_name}**\n- {r[0]:,} records\n- Total: {r[1]:,.2f}\n- Average: {r[2]:,.2f}"}
                        except Exception as e:
                            logger.debug(f"Revenue check failed for {table_name}: {e}")
                            pass
            return {"response": "Could not find revenue data in this database. Try asking about specific tables."}
        
        if any(k in ml for k in ["top","best","popular", "sample"]):
            # Return sample from first few tables
            for schema_name, table_name in all_tables[:3]:
                with engine.connect() as c:
                    try:
                        if isinstance(engine, DuckDBEngine):
                            q = f'"{schema_name}"."{table_name}"' if schema_name != "main" else f'"{table_name}"'
                            cols_result = c.execute(f"SELECT * FROM {q} LIMIT 3")
                            cols = [desc[0] for desc in cols_result.description] if hasattr(cols_result, 'description') else []
                            rows = cols_result.fetchall()
                        else:
                            q = f'"{schema_name}"."{table_name}"'
                            result = c.execute(text(f"SELECT * FROM {q} LIMIT 3"))
                            cols = list(result.keys()) if hasattr(result, 'keys') else []
                            rows = result.fetchall()
                        
                        row_str = "\n".join([str(row) for row in rows[:3]])
                        return {"response": f"🏆 **Sample from {table_name}:**\n```\n{row_str}\n```"}
                    except Exception as e:
                        logger.debug(f"Sample failed for {table_name}: {e}")
                        pass
            return {"response": "Could not retrieve sample data. The database may be empty or tables may have restricted access."}
        
        return {"response": f"🧠 **Neuro-Fabric Chat**\n\nI can help you explore your database. Try asking:\n\n• *How many rows in [table]?*\n• *List all tables*\n• *Show revenue stats*\n• *Sample from [table]*\n\n💡 Add `GOOGLE_API_KEY` to `.env` for AI-powered responses!"}
    except Exception as e:
        logger.error(f"Smart chat error: {e}")
        return {"response": f"Error: {e}"}

@app.post("/api/chat/reset")
async def reset_chat():
    global chat_thread_id
    chat_thread_id = str(uuid.uuid4())
    return {"status": "ok"}

# ── Artifacts ────────────────────────────────────────────────────────────────
@app.get("/api/artifacts")
async def get_artifacts():
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    return [{"path": str(p), "name": p.name, "size_kb": round(p.stat().st_size/1024, 1),
             "type": p.suffix.lstrip(".")} for p in sorted(OUTPUTS_DIR.glob("*.*"))]

@app.get("/api/artifacts/download/{filename}")
async def download_artifact(filename: str):
    path = OUTPUTS_DIR / filename
    if not path.exists(): raise HTTPException(404, "Not found")
    return FileResponse(path, filename=filename)

# ── Analytics ────────────────────────────────────────────────────────────────
@app.get("/api/analytics/overview")
async def analytics_overview():
    """Generate dynamic analytics overview from the connected database."""
    try:
        from core.db_connectors import get_inspector, list_schemas, DuckDBEngine
        from sqlalchemy import text
        
        if not _current_engine:
            return {
                "total_orders": 0, "unique_customers": 0, "total_revenue": 0,
                "recent_sales": [], "top_products": [], "error": "Connect to database first"
            }
            
        engine = _current_engine
        inspector = get_inspector(engine)
        
        # Dynamically discover tables
        all_tables = {}
        for sn in list_schemas(engine):
            try:
                tables = inspector.get_table_names(schema=sn)
                for tn in tables:
                    all_tables[f"{sn}.{tn}" if sn != "main" else tn] = (sn, tn)
            except Exception as e:
                logger.warning(f"Failed to list tables for schema {sn}: {e}")
        
        # Try to find common analytics tables by name patterns
        orders_table = None
        customers_table = None
        products_table = None
        sellers_table = None
        reviews_table = None
        order_items_table = None
        payments_table = None
        
        for full_name, (sn, tn) in all_tables.items():
            tn_lower = tn.lower()
            if 'order' in tn_lower and 'item' not in tn_lower and not orders_table:
                orders_table = (sn, tn)
            elif 'customer' in tn_lower or 'user' in tn_lower and not customers_table:
                customers_table = (sn, tn)
            elif 'product' in tn_lower or 'item' in tn_lower and not products_table:
                products_table = (sn, tn)
            elif 'seller' in tn_lower or 'vendor' in tn_lower and not sellers_table:
                sellers_table = (sn, tn)
            elif 'review' in tn_lower or 'rating' in tn_lower and not reviews_table:
                reviews_table = (sn, tn)
            elif 'order_item' in tn_lower or 'line_item' in tn_lower and not order_items_table:
                order_items_table = (sn, tn)
            elif 'payment' in tn_lower or 'transaction' in tn_lower and not payments_table:
                payments_table = (sn, tn)
        
        result = {
            "total_orders": 0,
            "unique_customers": 0,
            "total_revenue": 0,
            "avg_item_price": 0,
            "total_products": 0,
            "total_sellers": 0,
            "total_reviews": 0,
            "avg_review_score": 0,
            "order_status": {},
            "review_distribution": [],
            "payment_types": [],
            "tables_found": list(all_tables.keys())[:10]
        }
        
        with engine.connect() as c:
            # Orders analytics
            if orders_table:
                sn, tn = orders_table
                try:
                    q = f'"{sn}"."{tn}"' if sn != "main" else f'"{tn}"'
                    if isinstance(engine, DuckDBEngine):
                        orders = c.execute(f"SELECT COUNT(*), COUNT(DISTINCT customer_id) FROM {q}").fetchone()
                        status = c.execute(f"SELECT order_status, COUNT(*) FROM {q} GROUP BY 1 ORDER BY 2 DESC").fetchall()
                    else:
                        orders = c.execute(text(f"SELECT COUNT(*), COUNT(DISTINCT customer_id) FROM {q}")).fetchone()
                        status = c.execute(text(f"SELECT order_status, COUNT(*) FROM {q} GROUP BY 1 ORDER BY 2 DESC")).fetchall()
                    result["total_orders"] = orders[0]
                    result["unique_customers"] = orders[1]
                    result["order_status"] = {r[0]: r[1] for r in status} if status else {}
                except Exception as e:
                    logger.debug(f"Orders analytics failed: {e}")
            
            # Revenue from order_items or similar
            if order_items_table:
                sn, tn = order_items_table
                try:
                    q = f'"{sn}"."{tn}"' if sn != "main" else f'"{tn}"'
                    # Try to find price column
                    cols = inspector.get_columns(tn, schema=sn)
                    price_col = None
                    for col in cols:
                        col_name = col['name'].lower()
                        if 'price' in col_name or 'value' in col_name or 'amount' in col_name:
                            price_col = col['name']
                            break
                    
                    if price_col:
                        if isinstance(engine, DuckDBEngine):
                            rev = c.execute(f"SELECT COALESCE(SUM(\"{price_col}\"),0), COALESCE(AVG(\"{price_col}\"),0) FROM {q}").fetchone()
                        else:
                            rev = c.execute(text(f"SELECT COALESCE(SUM(\"{price_col}\"),0), COALESCE(AVG(\"{price_col}\"),0) FROM {q}")).fetchone()
                        result["total_revenue"] = round(float(rev[0]), 2)
                        result["avg_item_price"] = round(float(rev[1]), 2)
                except Exception as e:
                    logger.debug(f"Revenue analytics failed: {e}")
            
            # Products count
            if products_table:
                sn, tn = products_table
                try:
                    q = f'"{sn}"."{tn}"' if sn != "main" else f'"{tn}"'
                    if isinstance(engine, DuckDBEngine):
                        products = c.execute(f"SELECT COUNT(*) FROM {q}").fetchone()
                    else:
                        products = c.execute(text(f"SELECT COUNT(*) FROM {q}")).fetchone()
                    result["total_products"] = products[0]
                except Exception as e:
                    logger.debug(f"Products analytics failed: {e}")
            
            # Sellers count
            if sellers_table:
                sn, tn = sellers_table
                try:
                    q = f'"{sn}"."{tn}"' if sn != "main" else f'"{tn}"'
                    if isinstance(engine, DuckDBEngine):
                        sellers = c.execute(f"SELECT COUNT(*) FROM {q}").fetchone()
                    else:
                        sellers = c.execute(text(f"SELECT COUNT(*) FROM {q}")).fetchone()
                    result["total_sellers"] = sellers[0]
                except Exception as e:
                    logger.debug(f"Sellers analytics failed: {e}")
            
            # Reviews analytics
            if reviews_table:
                sn, tn = reviews_table
                try:
                    q = f'"{sn}"."{tn}"' if sn != "main" else f'"{tn}"'
                    # Try to find score/rating column
                    cols = inspector.get_columns(tn, schema=sn)
                    score_col = None
                    for col in cols:
                        col_name = col['name'].lower()
                        if 'score' in col_name or 'rating' in col_name or 'star' in col_name:
                            score_col = col['name']
                            break
                    
                    if score_col:
                        if isinstance(engine, DuckDBEngine):
                            reviews = c.execute(f"SELECT COUNT(*), COALESCE(AVG(\"{score_col}\"),0) FROM {q}").fetchone()
                            dist = c.execute(f"SELECT \"{score_col}\", COUNT(*) FROM {q} WHERE \"{score_col}\" IS NOT NULL GROUP BY 1 ORDER BY 1 DESC").fetchall()
                        else:
                            reviews = c.execute(text(f"SELECT COUNT(*), COALESCE(AVG(\"{score_col}\"),0) FROM {q}")).fetchone()
                            dist = c.execute(text(f"SELECT \"{score_col}\", COUNT(*) FROM {q} WHERE \"{score_col}\" IS NOT NULL GROUP BY 1 ORDER BY 1 DESC")).fetchall()
                        result["total_reviews"] = reviews[0]
                        result["avg_review_score"] = round(float(reviews[1]), 2)
                        result["review_distribution"] = [{"score": int(r[0]), "count": r[1]} for r in dist] if dist else []
                except Exception as e:
                    logger.debug(f"Reviews analytics failed: {e}")
            
            # Payments analytics
            if payments_table:
                sn, tn = payments_table
                try:
                    q = f'"{sn}"."{tn}"' if sn != "main" else f'"{tn}"'
                    cols = inspector.get_columns(tn, schema=sn)
                    type_col = None
                    for col in cols:
                        col_name = col['name'].lower()
                        if 'type' in col_name or 'method' in col_name:
                            type_col = col['name']
                            break
                    
                    if type_col:
                        if isinstance(engine, DuckDBEngine):
                            dist = c.execute(f"SELECT \"{type_col}\", COUNT(*) FROM {q} GROUP BY 1 ORDER BY 2 DESC LIMIT 5").fetchall()
                        else:
                            dist = c.execute(text(f"SELECT \"{type_col}\", COUNT(*) FROM {q} GROUP BY 1 ORDER BY 2 DESC LIMIT 5")).fetchall()
                        
                        result["payment_types"] = [{"type": str(r[0]), "count": r[1]} for r in dist] if dist else []
                except Exception as e:
                    logger.debug(f"Payments analytics failed: {e}")
        
        # Add basic stats about the database
        result["total_tables"] = len(all_tables)
        
        return result
    except Exception as e:
        logger.error("Analytics failed: %s", e)
        return {"error": str(e), "total_tables": 0}

# ── Supabase Setup ───────────────────────────────────────────────────────────
@app.post("/api/supabase/setup")
async def setup_supabase():
    """Create metadata tables in Supabase and seed with sample data."""
    try:
        from core.db_connectors import _build_supabase_url, create_engine, test_connection
        from core.config import SUPABASE_URL, SUPABASE_KEY
        from sqlalchemy import text
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            return {"success": False, "error": "SUPABASE_URL and SUPABASE_KEY must be set in .env"}
        
        url = _build_supabase_url()
        engine = create_engine(url, pool_pre_ping=True)
        
        if not test_connection(engine):
            return {"success": False, "error": "Could not connect to Supabase"}
        
        # SQL statements to create tables and seed data
        sql_statements = [
            # 1. Data Dictionary Table
            """
            CREATE TABLE IF NOT EXISTS data_dictionary (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                db_name VARCHAR(100) NOT NULL,
                table_name VARCHAR(255) NOT NULL,
                business_summary TEXT,
                column_descriptions JSONB DEFAULT '{}',
                usage_recommendations TEXT[] DEFAULT '{}',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE(db_name, table_name)
            )
            """,
            # 2. Chat History Table
            """
            CREATE TABLE IF NOT EXISTS chat_history (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id VARCHAR(255) NOT NULL,
                db_name VARCHAR(100) NOT NULL,
                role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                sql_query TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
            """,
            # 3. Quality Metrics Table
            """
            CREATE TABLE IF NOT EXISTS quality_metrics (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                db_name VARCHAR(100) NOT NULL,
                table_name VARCHAR(255) NOT NULL,
                row_count BIGINT,
                overall_completeness FLOAT,
                column_quality JSONB DEFAULT '[]',
                analyzed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE(db_name, table_name)
            )
            """,
            # 4. Schema Cache Table
            """
            CREATE TABLE IF NOT EXISTS schema_cache (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                db_name VARCHAR(100) NOT NULL,
                schema_hash VARCHAR(64),
                schema_data JSONB NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE(db_name)
            )
            """,
            # Create index
            "CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_history(session_id, created_at DESC)",
            # Enable RLS
            "ALTER TABLE IF EXISTS data_dictionary ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE IF EXISTS chat_history ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE IF EXISTS quality_metrics ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE IF EXISTS schema_cache ENABLE ROW LEVEL SECURITY",
            # Create policies
            "CREATE POLICY IF NOT EXISTS \"Allow public access\" ON data_dictionary FOR ALL USING (true) WITH CHECK (true)",
            "CREATE POLICY IF NOT EXISTS \"Allow public access\" ON chat_history FOR ALL USING (true) WITH CHECK (true)",
            "CREATE POLICY IF NOT EXISTS \"Allow public access\" ON quality_metrics FOR ALL USING (true) WITH CHECK (true)",
            "CREATE POLICY IF NOT EXISTS \"Allow public access\" ON schema_cache FOR ALL USING (true) WITH CHECK (true)",
            # Insert sample data
            """
            INSERT INTO data_dictionary (db_name, table_name, business_summary, column_descriptions, usage_recommendations) 
            VALUES 
            ('olist', 'orders', 'The orders table contains all customer purchase transactions in the Olist e-commerce platform. It tracks order status, timestamps, and customer-seller relationships.', 
             '{"order_id": "Unique identifier for each order", "customer_id": "Reference to the customer who placed the order", "order_status": "Current status of the order (delivered, shipped, etc.)", "order_purchase_timestamp": "When the order was placed"}',
             ARRAY['Join with customers table using customer_id', 'Use order_status to filter active vs completed orders', 'Analyze order_purchase_timestamp for temporal trends'])
            ON CONFLICT (db_name, table_name) DO NOTHING
            """,
            """
            INSERT INTO quality_metrics (db_name, table_name, row_count, overall_completeness, column_quality)
            VALUES 
            ('olist', 'orders', 99441, 0.95, '[{"column_name": "order_id", "null_rate": 0, "distinct_count": 99441}]')
            ON CONFLICT (db_name, table_name) DO NOTHING
            """
        ]
        
        executed = 0
        errors = []
        
        with engine.connect() as conn:
            for sql in sql_statements:
                try:
                    conn.execute(text(sql))
                    conn.commit()
                    executed += 1
                except Exception as e:
                    err_msg = str(e)
                    # Ignore "already exists" errors
                    if "already exists" not in err_msg.lower() and "duplicate" not in err_msg.lower():
                        errors.append(err_msg[:150])
        
        # Check if tables were created
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('data_dictionary', 'chat_history', 'quality_metrics', 'schema_cache')
            """))
            created_tables = [row[0] for row in result.fetchall()]
        
        return {
            "success": True, 
            "statements_executed": executed,
            "errors": errors if errors else None,
            "tables_created": created_tables,
            "message": f"Supabase setup complete! Created {len(created_tables)} tables."
        }
    except Exception as e:
        logger.error("Supabase setup failed: %s", e)
        return {"success": False, "error": str(e)}

@app.get("/api/supabase/status")
async def supabase_status():
    """Check Supabase connection and table status."""
    try:
        from core.db_connectors import _build_supabase_url, create_engine, test_connection
        from core.config import SUPABASE_URL, SUPABASE_KEY
        from sqlalchemy import text
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            return {"configured": False, "error": "SUPABASE_URL and SUPABASE_KEY not set"}
        
        url = _build_supabase_url()
        engine = create_engine(url, pool_pre_ping=True)
        
        if not test_connection(engine):
            return {"configured": True, "connected": False, "error": "Connection failed"}
        
        # Check for metadata tables
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('data_dictionary', 'chat_history', 'quality_metrics', 'schema_cache')
            """))
            tables = [row[0] for row in result.fetchall()]
            
            # Count rows in each table
            table_counts = {}
            for table in tables:
                try:
                    count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    table_counts[table] = count_result.fetchone()[0]
                except:
                    table_counts[table] = -1
        
        return {
            "configured": True,
            "connected": True,
            "metadata_tables": tables,
            "table_counts": table_counts,
            "engine_type": "supabase"
        }
    except Exception as e:
        logger.error("Supabase status check failed: %s", e)
        return {"configured": True, "connected": False, "error": str(e)}

# ── Helpers ──────────────────────────────────────────────────────────────────
def _ser(obj):
    if isinstance(obj, dict): return {k: _ser(v) for k, v in obj.items()}
    if isinstance(obj, list): return [_ser(v) for v in obj]
    try: json.dumps(obj); return obj
    except: return str(obj)

def _ser_val(v):
    if v is None: return None
    if isinstance(v, (int, float, bool, str)): return v
    from datetime import datetime, date
    if isinstance(v, datetime): return v.isoformat()
    if isinstance(v, date): return v.isoformat()
    return str(v)

# ── Neo4j Lineage Graph ──────────────────────────────────────────────────────

@app.get("/api/neo4j/status")
async def neo4j_status():
    """Check Neo4j connection status."""
    from core.neo4j_connector import is_available, NEO4J_URI
    return {"available": is_available(), "uri": NEO4J_URI}

@app.post("/api/neo4j/sync")
async def neo4j_sync():
    """Push current schema to Neo4j as a lineage graph."""
    from core.neo4j_connector import push_schema_to_neo4j
    schema = pipeline_state.get("schema", {})
    if not schema:
        # Try to build schema dynamically from DuckDB
        try:
            engine = _get_engine_forced()
            from core.db_connectors import get_inspector, DuckDBEngine
            inspector = get_inspector(engine)
            schema_name = "main" if isinstance(engine, DuckDBEngine) else "public"
            tables = inspector.get_table_names(schema=schema_name)
            for t in tables:
                cols = inspector.get_columns(t, schema=schema_name)
                schema[t] = {
                    "table_name": t, "schema_name": schema_name,
                    "columns": [{"name": c["name"], "data_type": str(c.get("type", c.get("data_type", ""))), "nullable": c.get("nullable", True), "is_primary_key": False, "is_foreign_key": False} for c in cols],
                    "foreign_keys": [], "row_count": 0,
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    result = push_schema_to_neo4j(schema)
    return result

@app.get("/api/neo4j/graph")
async def neo4j_graph():
    """Get the full lineage graph for visualization."""
    from core.neo4j_connector import get_full_graph
    return get_full_graph()

@app.get("/api/neo4j/lineage/{table}")
async def neo4j_lineage(table: str):
    """Get lineage for a specific table."""
    from core.neo4j_connector import get_lineage
    return get_lineage(table)


# ── GitHub Integration ───────────────────────────────────────────────────────

@app.get("/api/github/status")
async def github_status():
    """Check GitHub integration status."""
    from core.github_webhook import is_configured, GITHUB_REPO
    return {"configured": is_configured(), "repo": GITHUB_REPO}

@app.post("/api/github/webhook")
async def github_webhook(payload: dict):
    """Handle GitHub PR merge webhook events."""
    from core.github_webhook import handle_webhook
    return await handle_webhook(payload)

@app.get("/api/github/prs")
async def github_prs(state: str = "closed", per_page: int = 10):
    """Get recent PRs from the configured repository."""
    from core.github_webhook import get_recent_prs
    prs = await get_recent_prs(state=state, per_page=per_page)
    return {"prs": prs}

@app.get("/api/github/file")
async def github_file(path: str, ref: str = "main"):
    """Get file content from GitHub."""
    from core.github_webhook import get_file_content
    return await get_file_content(path=path, ref=ref)


# ── Serve Frontend ───────────────────────────────────────────────────────────
import os
from fastapi.staticfiles import StaticFiles

frontend_dist = Path(__file__).parent / "neuro-fabric" / "dist"
if frontend_dist.exists():
    # Mount the /assets directory for JS/CSS
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")
    
    # Serve index.html for the root path and any unhandled paths (for SPA routing)
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")

# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print("🧠 Neuro-Fabric API — http://localhost:8000")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
