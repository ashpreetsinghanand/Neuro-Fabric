"""
Database configuration for Bike Store services.
Uses Supabase PostgreSQL as the backing store.
"""
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/bike_store"
)

engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=10)


def get_connection():
    """Get a database connection from the pool."""
    return engine.connect()


def health_check():
    """Check database connectivity."""
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
