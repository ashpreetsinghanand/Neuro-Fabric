"""
Database connector factory — DuckDB-first with Postgres/Supabase fallback.

Usage:
    engine = get_engine()           # → DuckDB (default)
    engine = get_engine(db_config)  # → Postgres/Snowflake/MSSQL if url provided
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import duckdb
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from core.config import DATABASE_URL, SUPABASE_KEY, SUPABASE_URL

logger = logging.getLogger(__name__)

# ── DuckDB paths ─────────────────────────────────────────────────────────────
DUCKDB_PATH = Path(__file__).resolve().parent.parent / "data" / "neuro_fabric.duckdb"


# ── DuckDB wrappers (SQLAlchemy-compatible interface) ────────────────────────

class DuckDBResult:
    """Wraps a duckdb result to match SQLAlchemy result interface."""
    def __init__(self, raw, description):
        self._rows = raw
        self._desc = description or []
        self._col_names = [d[0] for d in self._desc] if self._desc else []

    def keys(self):
        return self._col_names

    def fetchall(self):
        return self._rows

    def fetchmany(self, n):
        return self._rows[:n]

    def fetchone(self):
        return self._rows[0] if self._rows else None


class DuckDBConnection:
    """Context-manager connection that accepts both raw SQL and SQLAlchemy text()."""
    def __init__(self, db_conn):
        self._conn = db_conn

    def execute(self, query, *args, **kwargs):
        # Unwrap SQLAlchemy text() objects to plain string
        sql = str(query) if not isinstance(query, str) else query
        sql = sql.strip()
        if not sql:
            return DuckDBResult([], [])
        try:
            raw = self._conn.execute(sql)
            desc = raw.description if hasattr(raw, 'description') else []
            rows = raw.fetchall() if desc else []
            return DuckDBResult(rows, desc)
        except Exception as e:
            logger.error("DuckDB execute error: %s", e)
            raise

    def close(self):
        pass  # DuckDB in-process, keep alive

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class DuckDBEngine:
    """SQLAlchemy Engine-like wrapper for DuckDB."""
    class _Dialect:
        name = "duckdb"
    dialect = _Dialect()

    def __init__(self, path: Path):
        self.path = path
        self._raw = duckdb.connect(str(path), read_only=False)
        logger.info("Connected to DuckDB: %s", path)

    def connect(self):
        return DuckDBConnection(self._raw)

    def dispose(self):
        self._raw.close()


class DuckDBInspector:
    """Inspector-like interface for DuckDB."""
    def __init__(self, engine: DuckDBEngine):
        self._raw = engine._raw

    def get_schema_names(self):
        rows = self._raw.execute(
            "SELECT DISTINCT schema_name FROM information_schema.schemata ORDER BY schema_name"
        ).fetchall()
        return [r[0] for r in rows]

    def get_table_names(self, schema=None):
        s = schema or "main"
        rows = self._raw.execute(
            f"SELECT table_name FROM information_schema.tables "
            f"WHERE table_schema='{s}' AND table_type='BASE TABLE' ORDER BY table_name"
        ).fetchall()
        return [r[0] for r in rows]

    def get_columns(self, table_name, schema=None):
        s = schema or "main"
        rows = self._raw.execute(
            f"SELECT column_name, data_type, is_nullable, column_default "
            f"FROM information_schema.columns "
            f"WHERE table_schema='{s}' AND table_name='{table_name}' "
            f"ORDER BY ordinal_position"
        ).fetchall()
        return [
            {"name": r[0], "type": r[1], "nullable": r[2] == "YES", "default": r[3]}
            for r in rows
        ]

    def get_pk_constraint(self, table_name, schema=None):
        return {"constrained_columns": [], "name": None}

    def get_foreign_keys(self, table_name, schema=None):
        return []

    def get_unique_constraints(self, table_name, schema=None):
        return []

    def get_check_constraints(self, table_name, schema=None):
        return []

    def get_indexes(self, table_name, schema=None):
        return []


# ── Engine cache ─────────────────────────────────────────────────────────────
_duckdb_engine: DuckDBEngine | None = None


def _build_supabase_url() -> str:
    if not SUPABASE_URL:
        raise ValueError("SUPABASE_URL is not configured.")
    ref = SUPABASE_URL.replace("https://", "").split(".")[0]
    return f"postgresql://postgres:{SUPABASE_KEY}@db.{ref}.supabase.co:5432/postgres"


def get_engine(db_config: dict[str, Any] | None = None) -> Engine | DuckDBEngine:
    """
    Return an engine. Priority:
    1. If db_config has a url → use it (Postgres/Snowflake/MSSQL).
    2. DATABASE_URL env var or Supabase → Postgres.
    3. Fallback → DuckDB local file.
    """
    global _duckdb_engine

    # Explicit URL provided
    if db_config and db_config.get("url"):
        url = db_config["url"]
        logger.info("Connecting with provided URL.")
        return create_engine(url, pool_pre_ping=True)

    # Priority: Postgres from DATABASE_URL (most common in production)
    if DATABASE_URL:
        logger.info("Using DATABASE_URL for SQL tools.")
        return create_engine(DATABASE_URL, pool_pre_ping=True)

    # Fallback: DuckDB local (only if no Postgres configured)
    if DUCKDB_PATH.exists():
        if _duckdb_engine is None:
            _duckdb_engine = DuckDBEngine(DUCKDB_PATH)
        return _duckdb_engine

    # Last resort: Supabase
    try:
        url = _build_supabase_url()
        logger.info("DuckDB not found; falling back to Supabase.")
        return create_engine(url, pool_pre_ping=True)
    except Exception:
        raise RuntimeError("No database configured.")


def get_inspector(engine):
    if isinstance(engine, DuckDBEngine):
        return DuckDBInspector(engine)
    return inspect(engine)


def test_connection(engine) -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1") if not isinstance(engine, DuckDBEngine) else "SELECT 1")
        return True
    except Exception as exc:
        logger.error("Connection test failed: %s", exc)
        return False


def list_schemas(engine) -> list[str]:
    inspector = get_inspector(engine)
    schemas = inspector.get_schema_names()
    # Exclude more internal Postgres schemas and views
    excluded = {
        "information_schema", "pg_catalog", "pg_toast", "pg_temp", 
        "auth", "storage", "graphql", "graphql_public", "realtime", 
        "pgsodium", "vault", "pgtle", "net", "pgstatmonitor", 
        "pg_temp_1", "pg_toast_temp_1", "supabase_functions", "supabase_migrations"
    }
    return [s for s in schemas if s not in excluded and not s.startswith("pg_")]


def get_db_type(engine) -> str:
    return engine.dialect.name
