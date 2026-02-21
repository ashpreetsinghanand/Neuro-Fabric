# Neuro-Fabric Architecture & Setup Guide

## Table of Contents

1. [What is Neuro-Fabric?](#1-what-is-neuro-fabric)
2. [MCP Server Connection Requirements](#2-mcp-server-connection-requirements)
3. [Full Credential Setup (.env)](#3-full-credential-setup-env)
4. [System Architecture](#4-system-architecture)
5. [LangGraph Pipeline Deep Dive](#5-langgraph-pipeline-deep-dive)
6. [Agent Responsibilities](#6-agent-responsibilities)
7. [Shared State (AgentState)](#7-shared-state-agentstate)
8. [Tools Reference](#8-tools-reference)
9. [Database Connection Modes](#9-database-connection-modes)
10. [Data Flow: End to End](#10-data-flow-end-to-end)
11. [Output Artifacts](#11-output-artifacts)
12. [Running the System](#12-running-the-system)

---

## 1. What is Neuro-Fabric?

Neuro-Fabric is a multi-agent AI platform that automatically generates comprehensive, AI-enhanced data dictionaries from enterprise databases. It connects to your database, extracts complete schema metadata, analyzes data quality, and uses **Gemini 3 Pro Preview** to generate business-friendly documentation — all through a conversational chat interface.

---

## 2. MCP Server Connection Requirements

The Supabase MCP (Model Context Protocol) server is how the agents talk to your Supabase project programmatically. Here is everything you need:

### Prerequisites

| Requirement | Why it's needed | How to get it |
|-------------|----------------|---------------|
| **Node.js >= 18** | The MCP server runs via `npx` | [nodejs.org](https://nodejs.org) |
| **Supabase account** | Your data lives here | [supabase.com](https://supabase.com) |
| **Supabase Project URL** | Identifies your project | Dashboard → Settings → API → Project URL |
| **Supabase Service Role Key** | Allows full DB access for schema inspection | Dashboard → Settings → API → `service_role` key (secret) |
| **Supabase Personal Access Token (PAT)** | Authenticates the MCP server subprocess | Dashboard → Account → Access Tokens → Generate new token |
| **Google API Key** | Powers Gemini 3 Pro Preview | [aistudio.google.com](https://aistudio.google.com) → Get API key |

### What each credential does

```
SUPABASE_URL  ──→  Tells the system which Supabase project to connect to
                   Example: https://abcdefghijkl.supabase.co

SUPABASE_KEY  ──→  Service role key for direct PostgreSQL access via SQLAlchemy
                   Used by: Schema Agent, Quality Agent (SQL execution)
                   ⚠ This is a SECRET — never commit it to git

SUPABASE_PAT  ──→  Personal Access Token for the Supabase MCP server subprocess
                   Used by: MCP Client (core/mcp_client.py)
                   This is different from the service role key — it authenticates
                   YOU as a user to the Supabase Management API
                   Get it at: supabase.com → Account (top right) → Access Tokens

GOOGLE_API_KEY ─→  Gemini 3 Pro Preview API key
                   Used by: ALL agents (schema, quality, ai_doc, chat, supervisor)
```

### How the MCP server is started

When any agent needs to use MCP tools, `core/mcp_client.py` spawns this subprocess:

```bash
npx -y @supabase/mcp-server-supabase@latest \
  --access-token <SUPABASE_PAT> \
  --project-ref <extracted from SUPABASE_URL>
```

The `langchain-mcp-adapters` library communicates with this process over **stdio transport**, converting its MCP tool definitions into LangChain-compatible tool objects that agents can call.

### Step-by-step: Getting your Supabase PAT

1. Go to [supabase.com](https://supabase.com) and log in
2. Click your **avatar / account icon** in the top-right corner
3. Select **Account** → **Access Tokens**
4. Click **Generate new token**
5. Give it a name (e.g. `neuro-fabric-mcp`)
6. Copy the token immediately — it won't be shown again
7. Paste it as `SUPABASE_PAT` in your `.env`

### Step-by-step: Getting your Service Role Key

1. Open your Supabase project dashboard
2. Go to **Settings** (gear icon) → **API**
3. Under **Project API Keys**, copy the `service_role` key (click the eye icon to reveal)
4. Paste it as `SUPABASE_KEY` in your `.env`
5. Also copy the **Project URL** for `SUPABASE_URL`

> **Important:** The `service_role` key bypasses Row Level Security (RLS). It's used for metadata inspection only. Do not expose it client-side.

---

## 3. Full Credential Setup (.env)

Copy `.env.example` to `.env` in the project root and fill in all values:

```env
# ── Google Gemini ──────────────────────────────────────────────────────────
GOOGLE_API_KEY=AIzaSy...your_key_here

# ── Supabase ───────────────────────────────────────────────────────────────
SUPABASE_URL=https://abcdefghijkl.supabase.co
SUPABASE_KEY=eyJhbGc...your_service_role_key_here
SUPABASE_PAT=sbp_...your_personal_access_token_here

# ── Optional: Enterprise DB override ──────────────────────────────────────
# Leave blank to use Supabase as the primary database
# PostgreSQL:  postgresql://user:password@host:5432/dbname
# SQL Server:  mssql+pymssql://user:password@host:1433/dbname
# Snowflake:   snowflake://user:password@account/dbname
DATABASE_URL=

# ── App Settings ───────────────────────────────────────────────────────────
LOG_LEVEL=INFO
OUTPUTS_DIR=outputs
```

---

## 4. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        User Interfaces                              │
│    Streamlit Web UI (app.py)        CLI (main.py)                   │
└────────────────────┬────────────────────────────────────────────────┘
                     │ AgentState (initial)
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LangGraph StateGraph                             │
│                                                                     │
│   START ──► [_pipeline_router] ──► Schema Agent                     │
│                    ▲                    │                           │
│                    │◄───────────────────┘ (state patch)             │
│                    │                                                │
│                    ├──────────────► Quality Agent                   │
│                    │                    │                           │
│                    │◄───────────────────┘                           │
│                    │                                                │
│                    ├──────────────► AI Doc Agent                    │
│                    │                    │                           │
│                    │◄───────────────────┘                           │
│                    │                                                │
│                    ├──────────────► Export Agent ──► END            │
│                    │                                                │
│                    └──────────────► Chat Agent ──► END              │
└─────────────────────────────────────────────────────────────────────┘
         │                   │                    │
         ▼                   ▼                    ▼
┌──────────────┐   ┌──────────────────┐  ┌───────────────────┐
│  SQLAlchemy  │   │  Supabase MCP    │  │  Gemini 3 Pro     │
│  Engine      │   │  Server (npx)    │  │  Preview (LLM)    │
│  (direct DB) │   │  (stdio)         │  │  (Google AI API)  │
└──────┬───────┘   └────────┬─────────┘  └───────────────────┘
       │                    │
       └────────────────────┘
                  │
       ┌──────────▼──────────┐
       │   Supabase (Postgres)│
       │   or Enterprise DB   │
       └─────────────────────┘
```

### Two Connectivity Layers

Neuro-Fabric uses **two parallel connection methods** to the database:

| Layer | How | Used By | Purpose |
|-------|-----|---------|---------|
| **SQLAlchemy** | Direct TCP to Postgres port 5432 | Schema Agent, Quality Agent | Fast SQL execution, schema inspection via `INFORMATION_SCHEMA` |
| **Supabase MCP** | `npx` subprocess via stdio | Chat Agent, MCP Client | Rich Supabase management API (migrations, table listing, policy inspection) |

---

## 5. LangGraph Pipeline Deep Dive

### Pipeline Graph (Full Documentation Run)

```
START
  │
  ▼ _pipeline_router() checks state
  │
  ├─── schema == {} ──────────► schema_agent_node()
  │                                    │
  │                             updates state.schema
  │                                    │
  │◄───────────────────────────────────┘ loops back to router
  │
  ├─── quality == {} ─────────► quality_agent_node()
  │                                    │
  │                             updates state.quality_report
  │                                    │
  │◄───────────────────────────────────┘
  │
  ├─── docs == {} ────────────► ai_doc_agent_node()
  │                                    │
  │                             updates state.documentation
  │                                    │
  │◄───────────────────────────────────┘
  │
  ├─── artifacts == [] ───────► export_agent_node()
  │                                    │
  │                             writes JSON + MD files
  │                             updates state.artifacts
  │                                    │
  │◄───────────────────────────────────┘
  │
  └─── all populated ─────────► END
```

### Chat Graph (Conversational Mode)

```
START
  │
  ▼
supervisor_node()   ← Gemini 3 Pro decides routing
  │
  ├─ "chat"      ──► chat_agent_node() ──► END
  ├─ "schema_agent" ──► schema_agent_node() ──► chat_agent_node() ──► END
  ├─ "quality_agent" ──► quality_agent_node() ──► chat_agent_node() ──► END
  └─ "done"      ──► END
```

### State Routing Logic

The `_pipeline_router` is a **deterministic function** (no LLM calls) that checks which fields of `AgentState` are populated and advances to the next required stage:

```python
def _pipeline_router(state):
    if not state["schema"]:       return "schema_agent"
    if not state["quality_report"]: return "quality_agent"
    if not state["documentation"]:  return "ai_doc_agent"
    if not state["artifacts"]:      return "export_agent"
    return "__end__"
```

This means the pipeline **always completes all stages in order**, with no risk of skipping steps.

### Incremental Update Detection

The Schema Agent computes an MD5 hash of the extracted schema and compares it against `outputs/schema_cache.json`. If identical, it reuses the cached version — avoiding redundant LLM calls on unchanged databases.

```
schema_cache.json exists?
  └─ YES → compare MD5 hash
             └─ MATCH → skip re-extraction, use cached
             └─ CHANGED → run fresh extraction, update cache
  └─ NO  → run fresh extraction, create cache
```

---

## 6. Agent Responsibilities

### Schema Agent (`agents/schema_agent.py`)

**Type:** ReAct agent (Gemini 3 Pro + tool loop)

**What it does:**
- Calls `list_all_schemas` to discover all non-system schemas
- For each table calls: `get_columns`, `get_foreign_keys`, `get_constraints`, `get_table_row_count`
- Assembles complete metadata into `state.schema`

**Tools used:** `list_all_schemas`, `list_tables`, `get_columns`, `get_foreign_keys`, `get_constraints`, `get_table_row_count`

**Output to state:**
```python
state["schema"] = {
    "orders": {
        "table_name": "orders",
        "schema_name": "public",
        "columns": [{"name": "id", "data_type": "INTEGER", "is_primary_key": True, ...}],
        "primary_keys": ["id"],
        "foreign_keys": [{"column": "user_id", "ref_table": "users", "ref_column": "id"}],
        "unique_constraints": [],
        "indexes": [...],
        "row_count": 48291
    }
}
```

---

### Quality Agent (`agents/quality_agent.py`)

**Type:** ReAct agent (Gemini 3 Pro + tool loop)

**What it does:**
- Per table: computes overall completeness (average non-null rate across all columns)
- Per column: null count, null rate, distinct count, min, max, mean, stddev
- PK health: what fraction of PK rows are actually unique
- Freshness: latest/oldest record timestamps for any timestamp column found

**Tools used:** `compute_table_completeness`, `analyze_column_nulls`, `analyze_column_stats`, `check_pk_uniqueness`, `check_freshness`

**Output to state:**
```python
state["quality_report"] = {
    "orders": {
        "row_count": 48291,
        "overall_completeness": 0.94,
        "pk_uniqueness_rate": 1.0,
        "freshness_column": "created_at",
        "freshness_latest": "2026-02-20 18:32:11",
        "column_quality": [
            {"column_name": "user_id", "null_rate": 0.0, "distinct_count": 12400, ...}
        ]
    }
}
```

---

### AI Documentation Agent (`agents/ai_doc_agent.py`)

**Type:** Direct LLM calls (no tool loop — pure generation)

**What it does:**
- Receives combined schema + quality context for each table
- Processes tables in batches of 10 (to fit context window)
- Calls Gemini 3 Pro Preview with temperature=0.2 for slight natural variation
- Generates: business summary, column descriptions, usage recommendations, related tables, SQL queries

**Model:** `gemini-3-pro-preview`, temperature=0.2

**Output to state:**
```python
state["documentation"] = {
    "orders": {
        "business_summary": "The orders table records all customer purchase transactions...",
        "column_descriptions": {
            "id": "Unique identifier for each order",
            "user_id": "References the customer who placed the order"
        },
        "usage_recommendations": ["Always join with users table via user_id", ...],
        "related_tables": ["users", "order_items", "products"],
        "suggested_queries": ["SELECT * FROM orders WHERE created_at > NOW() - INTERVAL '7 days'"]
    }
}
```

---

### Export Agent (`agents/export_agent.py`)

**Type:** Pure Python (no LLM calls)

**What it does:**
- Serializes `schema + quality_report + documentation` into two files per run
- JSON: full machine-readable dictionary
- Markdown: human-readable with tables, quality metrics, column descriptions, SQL examples
- Updates `schema_cache.json` for next incremental run

**Outputs:**
```
outputs/
├── my_database_20260221_143022.json    ← full structured data dictionary
├── my_database_20260221_143022.md      ← human-readable documentation
└── schema_cache.json                   ← incremental update hash cache
```

---

### Chat Agent (`agents/chat_agent.py`)

**Type:** ReAct agent (Gemini 3 Pro + tool loop)

**What it does:**
- Maintains conversation history across turns (via LangGraph MemorySaver checkpointer)
- Injects the full documented schema as context into every system prompt
- Can run live SQL queries via `execute_query` tool
- Can look up specific columns via `get_columns` tool
- Answers NL questions about schema, data quality, relationships, and usage

**Context injection:** Up to last 10 messages kept in context. Full schema summary (table summaries, column names, quality scores) injected into system prompt on every turn.

**Model:** `gemini-3-pro-preview`, temperature=0.1

**Example interactions:**
```
User:  "What does the orders table track?"
Agent: "The orders table records all customer purchase transactions including 
        48,291 orders. It has 94% data completeness and is joined to users 
        via user_id and to order_items via order_id..."

User:  "Write a query to find top 10 customers by revenue"
Agent: "Here's a query for that:
        SELECT u.id, u.email, SUM(o.total) AS revenue
        FROM users u JOIN orders o ON u.id = o.user_id
        GROUP BY u.id, u.email ORDER BY revenue DESC LIMIT 10"
```

---

### Supervisor (`agents/supervisor.py`)

**Pipeline mode:** Deterministic router — no LLM calls, no latency overhead. Simply checks which state fields are empty and routes accordingly.

**Chat mode:** LLM-powered (Gemini 3 Pro) — reads state + latest message and decides whether to call a specialist agent or go straight to chat.

---

## 7. Shared State (AgentState)

All agents read from and write patches to a single shared `AgentState` TypedDict. LangGraph merges patches automatically — agents only return the fields they changed.

```python
class AgentState(TypedDict):
    messages:       list              # full conversation history (auto-merged by add_messages)
    db_config:      dict              # {"url": "...", "name": "my_db"}
    schema:         dict[str, TableSchema]
    quality_report: dict[str, TableQuality]
    documentation:  dict[str, TableDocumentation]
    artifacts:      list[str]         # absolute file paths
    current_task:   str               # "pipeline" | "chat" | "schema_agent" | ...
    errors:         list[str]         # non-fatal errors accumulated across agents
```

Each agent returns **only the keys it modifies**:

```python
# Schema agent returns:
return {"schema": {...}, "errors": [...]}

# Quality agent returns:
return {"quality_report": {...}}

# AI doc agent returns:
return {"documentation": {...}}

# Chat agent returns:
return {"messages": [AIMessage(content="...")]}
```

---

## 8. Tools Reference

### Schema Tools (`tools/schema_tools.py`)

| Tool | SQL / SQLAlchemy | What it returns |
|------|-----------------|-----------------|
| `list_all_schemas` | `inspector.get_schema_names()` | All non-system schema names |
| `list_tables` | `inspector.get_table_names(schema)` | All tables in a schema |
| `get_columns` | `inspector.get_columns()` + `get_pk_constraint()` | Column names, types, nullability, PK flag |
| `get_foreign_keys` | `inspector.get_foreign_keys()` | FK column, referenced table + column |
| `get_constraints` | `inspector.get_unique_constraints()` + `get_check_constraints()` + `get_indexes()` | All constraint and index metadata |
| `get_table_row_count` | `SELECT COUNT(*) FROM table` | Exact row count |

### Quality Tools (`tools/quality_tools.py`)

| Tool | SQL | What it returns |
|------|-----|-----------------|
| `compute_table_completeness` | `AVG(CASE WHEN col IS NULL ...)` per column | Overall completeness score + per-column null rates |
| `analyze_column_nulls` | `COUNT(*) FILTER (WHERE col IS NULL)` | Null count and null rate |
| `analyze_column_stats` | `MIN`, `MAX`, `COUNT(DISTINCT)`, `AVG`, `STDDEV` | Statistical profile of a column |
| `check_pk_uniqueness` | `COUNT(DISTINCT pk_cols) / COUNT(*)` | PK uniqueness health ratio |
| `check_freshness` | `MAX(ts_col)`, `MIN(ts_col)`, `NOW() - MAX(ts_col)` | Latest/oldest record, age in days |

### SQL Tools (`tools/sql_tools.py`)

| Tool | What it does |
|------|-------------|
| `execute_query` | Runs any `SELECT`/`WITH` query, returns up to 100 rows as JSON |
| `get_sample_rows` | Returns up to 20 sample rows from a table |

> **Safety:** `execute_query` rejects any query not starting with `SELECT` or `WITH`. No writes permitted.

### Export Tools (`tools/export_tools.py`)

| Tool | What it does |
|------|-------------|
| `write_json_artifact` | Writes full state as pretty-printed JSON to `outputs/` |
| `write_markdown_artifact` | Generates rich Markdown with quality tables, column docs, SQL examples |
| `write_schema_cache` | Persists schema snapshot for incremental update detection |

---

## 9. Database Connection Modes

### Connection Priority (automatic fallback)

```
1. db_config["url"]   → explicit URL provided by user (any dialect)
2. db_config["type"]  → "supabase" or "postgres" → builds URL from env vars
3. DATABASE_URL env   → any SQLAlchemy-compatible URL
4. Default            → Supabase URL built from SUPABASE_URL + SUPABASE_KEY
```

### Supported Databases

| Database | Connection URL format | Notes |
|----------|----------------------|-------|
| **Supabase** | Auto-built from env | Default mode |
| **PostgreSQL** | `postgresql://user:pass@host:5432/db` | Any Postgres |
| **Snowflake** | `snowflake://user:pass@account/db` | Needs `snowflake-sqlalchemy` |
| **SQL Server** | `mssql+pymssql://user:pass@host:1433/db` | Needs `pymssql` |

### How the Supabase URL is built automatically

```
SUPABASE_URL = https://abcdefghijkl.supabase.co
SUPABASE_KEY = eyJhbGc...

→ ref = "abcdefghijkl"
→ SQLAlchemy URL = postgresql://postgres:<KEY>@db.abcdefghijkl.supabase.co:5432/postgres
```

---

## 10. Data Flow: End to End

```
User triggers pipeline
        │
        ▼
AgentState initialized
{schema: {}, quality: {}, docs: {}, artifacts: []}
        │
        ▼
Schema Agent runs
  → npx spawns Supabase MCP server (or SQLAlchemy direct)
  → lists all schemas and tables
  → for each table: get columns, FKs, constraints, row count
  → Gemini 3 Pro assembles into structured JSON
  → state.schema = {table → TableSchema}
        │
        ▼
Quality Agent runs
  → for each table in state.schema:
      → SQL: compute null rates, stats, completeness
      → SQL: check PK uniqueness
      → SQL: check timestamp freshness
  → Gemini 3 Pro formats into quality report
  → state.quality_report = {table → TableQuality}
        │
        ▼
AI Documentation Agent runs
  → batches tables (10 per batch)
  → for each batch: sends schema + quality to Gemini 3 Pro
  → Gemini generates: business summary, column descriptions,
    usage recommendations, related tables, SQL examples
  → state.documentation = {table → TableDocumentation}
        │
        ▼
Export Agent runs
  → merges schema + quality + docs
  → writes outputs/{name}_{timestamp}.json
  → writes outputs/{name}_{timestamp}.md
  → writes outputs/schema_cache.json
  → state.artifacts = ["/path/to/json", "/path/to/md"]
        │
        ▼
Pipeline ends → artifacts available for download
```

---

## 11. Output Artifacts

### JSON (`outputs/{name}_{ts}.json`)

```json
{
  "database": "my_database",
  "schema": {
    "orders": {
      "table_name": "orders",
      "columns": [...],
      "primary_keys": ["id"],
      "foreign_keys": [{"column": "user_id", "ref_table": "users", "ref_column": "id"}],
      "row_count": 48291
    }
  },
  "quality_report": {
    "orders": {
      "overall_completeness": 0.94,
      "pk_uniqueness_rate": 1.0,
      "freshness_latest": "2026-02-20 18:32:11",
      "column_quality": [...]
    }
  },
  "documentation": {
    "orders": {
      "business_summary": "Records all customer purchase transactions...",
      "column_descriptions": {"id": "Unique order identifier"},
      "usage_recommendations": [...],
      "suggested_queries": [...]
    }
  }
}
```

### Markdown (`outputs/{name}_{ts}.md`)

Includes for each table:
- Business summary (AI-generated)
- Quality metrics table (row count, completeness %, PK health, latest record)
- Full column table (name, type, nullable, PK/FK flags, null rate, distinct count, description)
- Relationship diagram (FK references)
- Statistical highlights (min/max/mean/stddev for numeric columns)
- Usage recommendations
- Suggested SQL queries with syntax highlighting

---

## 12. Running the System

### Install

```bash
pip install -r requirements.txt
```

Node.js must be installed for MCP (check with `node --version`).

### Configure

```bash
cp .env.example .env
# edit .env with your credentials
```

### CLI — Full Pipeline

```bash
python main.py --name my_project
```

### CLI — Pipeline + Chat

```bash
python main.py --name my_project --chat
```

### CLI — Chat Only (using existing artifacts)

```bash
python main.py --chat-only
```

### CLI — Schema Only

```bash
python main.py --schema-only --name my_project
```

### Web UI (Streamlit)

```bash
streamlit run app.py
```

Opens at `http://localhost:8501` with:
- **Chat tab** — conversational data assistant
- **Schema Browser** — interactive table/column explorer
- **Quality Dashboard** — completeness and statistics tables
- **Documentation** — AI-generated business descriptions
- **Artifacts** — download JSON/Markdown files
