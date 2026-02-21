import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Google Gemini
GOOGLE_API_KEY: str = os.environ.get("GOOGLE_API_KEY", "")
GEMINI_MODEL: str = "gemini-3-pro-preview"

# Supabase
SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY", "")
SUPABASE_PAT: str = os.environ.get("SUPABASE_PAT", "")

# Optional enterprise DB
DATABASE_URL: str = os.environ.get("DATABASE_URL", "")

# Paths
BASE_DIR: Path = Path(__file__).resolve().parent.parent
OUTPUTS_DIR: Path = BASE_DIR / os.environ.get("OUTPUTS_DIR", "outputs")
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

SCHEMA_CACHE_FILE: Path = OUTPUTS_DIR / "schema_cache.json"

# Logging
LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")


def validate_config() -> list[str]:
    """Return a list of missing required config keys."""
    missing = []
    if not GOOGLE_API_KEY:
        missing.append("GOOGLE_API_KEY")
    if not SUPABASE_URL:
        missing.append("SUPABASE_URL")
    if not SUPABASE_KEY:
        missing.append("SUPABASE_KEY")
    return missing
