"""
Database connector factory supporting DuckDB (local-first), Postgres, Snowflake, and SQL Server.

DuckDB is the primary engine for local-first, privacy-focused analytics.
Postgres/Supabase is used as a cloud fallback.

Usage:
    engine = get_engine(db_config)
    # db_config = {"url": "duckdb:///path/to/db.duckdb"}
    # or         {"url": "postgresql://..."}
    # or         {}  → falls back to local DuckDB
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import duckdb
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine, Inspector

from core.config import DATABASE_URL, SUPABASE_KEY, SUPABASE_URL

logger = logging.getLogger(__name__)

# ── DuckDB Paths ─────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent
DUCKDB_PATH = BASE_DIR / "data" / "neuro_fabric.duckdb"


# ── DuckDB Wrapper (SQLAlchemy-compatible interface) ─────────────────────────

class DuckDBEngine:
    """Wraps DuckDB connection to provide a SQLAlchemy-like interface."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or str(DUCKDB_PATH)
        self._conn = None
        self.dialect = type("Dialect", (), {"name": "duckdb"})()
        self.url = type("URL", (), {"database": self.db_path})()

    def _get_conn(self):
        if self._conn is None:
            self._conn = duckdb.connect(self.db_path, read_only=False)
        return self._conn

    def connect(self):
        return DuckDBConnection(self._get_conn())

    def dispose(self):
        if self._conn:
            self._conn.close()
            self._conn = None


class DuckDBConnection:
    """Context-manager wrapper for DuckDB connection."""

    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute(self, query, params=None):
        sql = str(query) if hasattr(query, 'text') else str(query)
        try:
            result = self.conn.execute(sql)
            return DuckDBResult(result)
        except Exception as e:
            logger.error("DuckDB query failed: %s", e)
            raise


class DuckDBResult:
    """Wraps DuckDB result for SQLAlchemy-compatible interface."""

    def __init__(self, result):
        self._result = result
        self._description = result.description if result.description else []

    def keys(self):
        return [d[0] for d in self._description]

    def fetchall(self):
        return self._result.fetchall()

    def fetchmany(self, size=100):
        rows = self._result.fetchall()
        return rows[:size]

    def fetchone(self):
        return self._result.fetchone()

    def scalar(self):
        row = self.fetchone()
        return row[0] if row else None

    def mappings(self):
        return DuckDBMappingResult(self._result, self._description)


class DuckDBMappingResult:
    """Provides dict-like row access."""

    def __init__(self, result, description):
        self._result = result
        self._keys = [d[0] for d in description]

    def one(self):
        row = self._result.fetchone()
        if row is None:
            raise Exception("No rows returned")
        return dict(zip(self._keys, row))

    def all(self):
        rows = self._result.fetchall()
        return [dict(zip(self._keys, row)) for row in rows]


# ── DuckDB Inspector ─────────────────────────────────────────────────────────

class DuckDBInspector:
    """Provides SQLAlchemy Inspector-like interface for DuckDB."""

    def __init__(self, engine: DuckDBEngine):
        self.engine = engine
        self.conn = engine._get_conn()

    def get_schema_names(self):
        result = self.conn.execute("SELECT DISTINCT schema_name FROM information_schema.schemata ORDER BY schema_name")
        return [r[0] for r in result.fetchall()]

    def get_table_names(self, schema="main"):
        result = self.conn.execute(f"""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = '{schema}' AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        return [r[0] for r in result.fetchall()]

    def get_columns(self, table_name, schema="main"):
        result = self.conn.execute(f"""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = '{schema}' AND table_name = '{table_name}'
            ORDER BY ordinal_position
        """)
        pk_cols = set(self.get_pk_constraint(table_name, schema=schema).get("constrained_columns", []))
        columns = []
        for row in result.fetchall():
            columns.append({
                "name": row[0],
                "type": row[1],
                "nullable": row[2] == "YES",
                "default": row[3],
            })
        return columns

    def get_pk_constraint(self, table_name, schema="main"):
        try:
            result = self.conn.execute(f"""
                SELECT kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                WHERE tc.table_schema = '{schema}'
                    AND tc.table_name = '{table_name}'
                    AND tc.constraint_type = 'PRIMARY KEY'
            """)
            cols = [r[0] for r in result.fetchall()]
            return {"constrained_columns": cols, "name": f"{table_name}_pkey"}
        except Exception:
            return {"constrained_columns": [], "name": None}

    def get_foreign_keys(self, table_name, schema="main"):
        try:
            result = self.conn.execute(f"""
                SELECT
                    kcu.column_name AS from_column,
                    ccu.table_name AS to_table,
                    ccu.column_name AS to_column,
                    tc.constraint_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage ccu
                    ON tc.constraint_name = ccu.constraint_name
                WHERE tc.table_schema = '{schema}'
                    AND tc.table_name = '{table_name}'
                    AND tc.constraint_type = 'FOREIGN KEY'
            """)
            fks = []
            for row in result.fetchall():
                fks.append({
                    "constrained_columns": [row[0]],
                    "referred_table": row[1],
                    "referred_schema": schema,
                    "referred_columns": [row[2]],
                    "name": row[3],
                })
            return fks
        except Exception:
            return []

    def get_unique_constraints(self, table_name, schema="main"):
        return []

    def get_check_constraints(self, table_name, schema="main"):
        return []

    def get_indexes(self, table_name, schema="main"):
        return []


# ── Public API ────────────────────────────────────────────────────────────────

_duckdb_engine_cache: DuckDBEngine | None = None


def get_engine(db_config: dict[str, Any] | None = None) -> DuckDBEngine | Engine:
    """
    Return a database engine.

    Priority:
    1. db_config["url"] if provided (SQLAlchemy for Postgres, etc.)
    2. DATABASE_URL env var
    3. Local DuckDB (default — local-first)
    """
    global _duckdb_engine_cache

    if db_config and db_config.get("url"):
        url = db_config["url"]
        if "duckdb" in url:
            path = url.replace("duckdb:///", "")
            return DuckDBEngine(path)
        logger.info("Connecting with provided URL.")
        return create_engine(url, pool_pre_ping=True)

    if DATABASE_URL and "postgresql" in DATABASE_URL:
        try:
            engine = create_engine(DATABASE_URL, pool_pre_ping=True)
            # Quick test
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Connected to PostgreSQL via DATABASE_URL.")
            return engine
        except Exception as e:
            logger.warning("PostgreSQL connection failed (%s), falling back to DuckDB.", e)

    # Default: Local DuckDB
    if _duckdb_engine_cache is None:
        if not DUCKDB_PATH.exists():
            logger.warning("DuckDB file not found at %s. Run `python3 scripts/seed_duckdb.py` first.", DUCKDB_PATH)
        _duckdb_engine_cache = DuckDBEngine(str(DUCKDB_PATH))
        logger.info("Connected to local DuckDB: %s", DUCKDB_PATH)

    return _duckdb_engine_cache


def get_inspector(engine) -> DuckDBInspector | Inspector:
    """Return an inspector for the given engine."""
    if isinstance(engine, DuckDBEngine):
        return DuckDBInspector(engine)
    return inspect(engine)


def test_connection(engine) -> bool:
    """Return True if the database connection is healthy."""
    try:
        if isinstance(engine, DuckDBEngine):
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            return True
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("Connection test failed: %s", exc)
        return False


def list_schemas(engine) -> list[str]:
    """Return all non-system schema names."""
    inspector = get_inspector(engine)
    if isinstance(inspector, DuckDBInspector):
        schemas = inspector.get_schema_names()
        excluded = {"information_schema", "pg_catalog"}
        return [s for s in schemas if s not in excluded]
    schemas = inspector.get_schema_names()
    excluded = {"information_schema", "pg_catalog", "pg_toast"}
    return [s for s in schemas if s not in excluded]


def get_db_type(engine) -> str:
    """Return a string identifying the DB dialect."""
    if isinstance(engine, DuckDBEngine):
        return "duckdb"
    return engine.dialect.name


def get_duckdb_connection():
    """Get a raw DuckDB connection for advanced analytics."""
    return duckdb.connect(str(DUCKDB_PATH), read_only=True)
