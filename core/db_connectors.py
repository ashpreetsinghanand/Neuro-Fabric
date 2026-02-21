"""
Database connector factory supporting Postgres (Supabase), Snowflake, and SQL Server.

Usage:
    engine = get_engine(db_config)
    # db_config = {"type": "postgres", "url": "postgresql://..."}
    # or         {"type": "snowflake", "url": "snowflake://..."}
    # or         {"type": "mssql",     "url": "mssql+pymssql://..."}
    # or         {}  → falls back to DATABASE_URL from config
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, Inspector, inspect

from core.config import DATABASE_URL, SUPABASE_KEY, SUPABASE_URL

logger = logging.getLogger(__name__)


class DBType(str, Enum):
    POSTGRES = "postgres"
    SNOWFLAKE = "snowflake"
    MSSQL = "mssql"
    SUPABASE = "supabase"  # Supabase is Postgres under the hood


def _build_supabase_url() -> str:
    """Construct a SQLAlchemy Postgres URL from Supabase credentials."""
    if not SUPABASE_URL:
        raise ValueError("SUPABASE_URL is not configured.")
    # Supabase exposes a direct Postgres connection on port 5432
    # URL format: https://<ref>.supabase.co  →  postgresql://postgres:<key>@db.<ref>.supabase.co:5432/postgres
    ref = SUPABASE_URL.replace("https://", "").split(".")[0]
    return f"postgresql://postgres:{SUPABASE_KEY}@db.{ref}.supabase.co:5432/postgres"


def get_engine(db_config: dict[str, Any] | None = None) -> Engine:
    """
    Return a SQLAlchemy Engine.

    Priority:
    1. db_config["url"] if provided
    2. Infer from db_config["type"] + db_config fields
    3. DATABASE_URL env var
    4. Supabase URL constructed from SUPABASE_URL + SUPABASE_KEY
    """
    if db_config:
        if "url" in db_config and db_config["url"]:
            url = db_config["url"]
            logger.info("Connecting with provided URL (type masked).")
            return create_engine(url, pool_pre_ping=True)

        db_type = db_config.get("type", "").lower()
        if db_type in (DBType.SUPABASE, DBType.POSTGRES):
            url = _build_supabase_url()
            return create_engine(url, pool_pre_ping=True)

    if DATABASE_URL:
        logger.info("Connecting using DATABASE_URL from environment.")
        return create_engine(DATABASE_URL, pool_pre_ping=True)

    # Default: Supabase direct connection
    logger.info("Connecting to Supabase (default).")
    url = _build_supabase_url()
    return create_engine(url, pool_pre_ping=True)


def get_inspector(engine: Engine) -> Inspector:
    return inspect(engine)


def test_connection(engine: Engine) -> bool:
    """Return True if the database connection is healthy."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("Connection test failed: %s", exc)
        return False


def list_schemas(engine: Engine) -> list[str]:
    """Return all non-system schema names."""
    inspector = get_inspector(engine)
    schemas = inspector.get_schema_names()
    # Filter out internal schemas for Postgres/Supabase
    excluded = {"information_schema", "pg_catalog", "pg_toast"}
    return [s for s in schemas if s not in excluded]


def get_db_type(engine: Engine) -> str:
    """Return a string identifying the DB dialect."""
    return engine.dialect.name
