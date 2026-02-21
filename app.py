"""
Neuro-Fabric Streamlit Chat UI.

Provides:
- Database connection configuration sidebar
- Full pipeline trigger (schema → quality → docs → export)
- Conversational chat interface powered by the chat agent
- Schema browser and quality dashboard tabs
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

import streamlit as st

from core.config import OUTPUTS_DIR, validate_config
from core.db_connectors import get_engine, test_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Neuro-Fabric | Data Dictionary",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------

def init_session():
    defaults = {
        "thread_id": str(uuid.uuid4()),
        "chat_history": [],
        "pipeline_state": {},
        "pipeline_run": False,
        "db_config": {},
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


init_session()


# ---------------------------------------------------------------------------
# Sidebar: DB Configuration
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("🧠 Neuro-Fabric")
    st.caption("AI-Powered Data Dictionary Platform")
    st.divider()

    st.subheader("Database Connection")
    db_type = st.selectbox(
        "Database Type",
        ["Supabase (default)", "PostgreSQL", "Snowflake", "SQL Server"],
        key="db_type_select",
    )

    use_custom = st.checkbox("Use custom connection URL", value=False)
    db_url = ""
    if use_custom:
        db_url = st.text_input("Connection URL", type="password", placeholder="postgresql://user:pass@host/db")

    db_name = st.text_input("Database / Project Name", value="my_database",
                             help="Used for naming artifact files.")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        test_btn = st.button("Test Connection", use_container_width=True)
    with col2:
        run_pipeline_btn = st.button("▶ Run Pipeline", type="primary", use_container_width=True)

    if test_btn:
        with st.spinner("Testing connection..."):
            try:
                db_config = {"url": db_url, "name": db_name} if db_url else {"name": db_name}
                engine = get_engine(db_config)
                ok = test_connection(engine)
                if ok:
                    st.success("Connection successful!")
                else:
                    st.error("Connection failed. Check your credentials.")
            except Exception as e:
                st.error(f"Error: {e}")

    # Config validation warnings
    missing = validate_config()
    if missing:
        st.warning(f"Missing env vars: {', '.join(missing)}")

    st.divider()
    st.caption("Artifacts are saved to: `outputs/`")

    # List existing artifacts
    artifacts = sorted(OUTPUTS_DIR.glob("*.json")) + sorted(OUTPUTS_DIR.glob("*.md"))
    if artifacts:
        st.subheader("Saved Artifacts")
        for artifact in artifacts[-10:]:
            st.code(artifact.name, language=None)


# ---------------------------------------------------------------------------
# Pipeline Runner
# ---------------------------------------------------------------------------

def run_full_pipeline(db_config: dict):
    """Run the full schema → quality → docs → export pipeline."""
    from agents.supervisor import get_pipeline_app

    app = get_pipeline_app()
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

    progress = st.progress(0, text="Starting pipeline...")
    status_placeholder = st.empty()

    steps = [
        ("Schema Extraction", 25),
        ("Quality Analysis", 50),
        ("AI Documentation", 75),
        ("Export Artifacts", 100),
    ]
    step_idx = 0

    final_state = None
    for event in app.stream(initial_state, stream_mode="values"):
        final_state = event
        schema_done = bool(event.get("schema"))
        quality_done = bool(event.get("quality_report"))
        docs_done = bool(event.get("documentation"))
        artifacts_done = bool(event.get("artifacts"))

        if artifacts_done:
            progress.progress(100, text="Pipeline complete!")
        elif docs_done:
            progress.progress(75, text="Generating AI documentation...")
        elif quality_done:
            progress.progress(50, text="Analyzing data quality...")
        elif schema_done:
            progress.progress(25, text="Extracting schema...")

        errors = event.get("errors", [])
        if errors:
            for err in errors:
                st.warning(f"⚠ {err}")

    return final_state


if run_pipeline_btn:
    db_config = {"url": db_url if db_url else "", "name": db_name}
    with st.spinner("Running Neuro-Fabric pipeline..."):
        try:
            final_state = run_full_pipeline(db_config)
            if final_state:
                st.session_state["pipeline_state"] = final_state
                st.session_state["pipeline_run"] = True
                artifacts = final_state.get("artifacts", [])
                st.success(f"Pipeline complete! {len(artifacts)} artifacts written.")
                for art in artifacts:
                    st.code(art)
        except Exception as e:
            st.error(f"Pipeline failed: {e}")
            logger.exception("Pipeline error")


# ---------------------------------------------------------------------------
# Main Content Tabs
# ---------------------------------------------------------------------------

tab_chat, tab_schema, tab_quality, tab_docs, tab_artifacts = st.tabs([
    "💬 Chat",
    "🗂 Schema Browser",
    "📊 Quality Dashboard",
    "📖 Documentation",
    "📁 Artifacts",
])


# ── Chat Tab ──────────────────────────────────────────────────────────────

with tab_chat:
    st.header("Natural Language Data Assistant")

    if not st.session_state["pipeline_run"]:
        st.info(
            "Run the pipeline first (sidebar → ▶ Run Pipeline) to load your database schema, "
            "or start chatting — the assistant can help guide you."
        )

    # Display chat history
    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask anything about your database..."):
        st.session_state["chat_history"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    from langchain_core.messages import HumanMessage
                    from agents.supervisor import get_chat_app

                    chat_app = get_chat_app()
                    pipeline_state = st.session_state.get("pipeline_state", {})
                    db_config = {"url": db_url if db_url else "", "name": db_name}

                    # Merge pipeline state with current chat turn
                    chat_input = {
                        "messages": [HumanMessage(content=prompt)],
                        "db_config": db_config,
                        "schema": pipeline_state.get("schema", {}),
                        "quality_report": pipeline_state.get("quality_report", {}),
                        "documentation": pipeline_state.get("documentation", {}),
                        "artifacts": pipeline_state.get("artifacts", []),
                        "current_task": "chat",
                        "errors": [],
                    }

                    config = {"configurable": {"thread_id": st.session_state["thread_id"]}}
                    result = chat_app.invoke(chat_input, config=config)
                    ai_messages = result.get("messages", [])
                    response = ai_messages[-1].content if ai_messages else "I couldn't generate a response."

                    st.markdown(response)
                    st.session_state["chat_history"].append({"role": "assistant", "content": response})

                except Exception as e:
                    err_msg = f"Error: {e}"
                    st.error(err_msg)
                    logger.exception("Chat error")


# ── Schema Browser Tab ────────────────────────────────────────────────────

with tab_schema:
    st.header("Schema Browser")
    state = st.session_state.get("pipeline_state", {})
    schema = state.get("schema", {})

    if not schema:
        st.info("Run the pipeline to populate the schema browser.")
    else:
        st.metric("Total Tables", len(schema))
        selected_table = st.selectbox("Select a table", sorted(schema.keys()))
        if selected_table:
            table_data = schema[selected_table]
            st.subheader(f"`{selected_table}`")

            col1, col2, col3 = st.columns(3)
            col1.metric("Columns", len(table_data.get("columns", [])))
            col2.metric("Row Count", f"{table_data.get('row_count', 'N/A'):,}" if isinstance(table_data.get('row_count'), int) else "N/A")
            col3.metric("Primary Keys", len(table_data.get("primary_keys", [])))

            st.subheader("Columns")
            import pandas as pd
            cols_df = pd.DataFrame(table_data.get("columns", []))
            if not cols_df.empty:
                st.dataframe(cols_df, use_container_width=True)

            fks = table_data.get("foreign_keys", [])
            if fks:
                st.subheader("Foreign Keys")
                fk_df = pd.DataFrame(fks)
                st.dataframe(fk_df, use_container_width=True)

            indexes = table_data.get("indexes", [])
            if indexes:
                st.subheader("Indexes")
                st.json(indexes)


# ── Quality Dashboard Tab ─────────────────────────────────────────────────

with tab_quality:
    st.header("Data Quality Dashboard")
    state = st.session_state.get("pipeline_state", {})
    quality = state.get("quality_report", {})

    if not quality:
        st.info("Run the pipeline to populate the quality dashboard.")
    else:
        import pandas as pd

        # Summary table
        summary_rows = []
        for table_name, q in quality.items():
            summary_rows.append({
                "Table": table_name,
                "Row Count": q.get("row_count", 0),
                "Completeness": f"{q.get('overall_completeness', 0) * 100:.1f}%",
                "PK Uniqueness": f"{q.get('pk_uniqueness_rate', 1.0) * 100:.1f}%" if q.get('pk_uniqueness_rate') is not None else "N/A",
                "Latest Record": q.get("freshness_latest", "N/A"),
            })

        st.subheader("Table Overview")
        df = pd.DataFrame(summary_rows)
        st.dataframe(df, use_container_width=True)

        # Per-table deep dive
        st.divider()
        selected = st.selectbox("Drill into table", sorted(quality.keys()), key="quality_table_select")
        if selected:
            q = quality[selected]
            st.subheader(f"Quality Details: `{selected}`")
            col_quality = q.get("column_quality", [])
            if col_quality:
                cq_df = pd.DataFrame(col_quality)
                st.dataframe(cq_df, use_container_width=True)


# ── Documentation Tab ─────────────────────────────────────────────────────

with tab_docs:
    st.header("AI-Generated Documentation")
    state = st.session_state.get("pipeline_state", {})
    docs = state.get("documentation", {})
    schema = state.get("schema", {})

    if not docs:
        st.info("Run the pipeline to generate AI documentation.")
    else:
        selected_doc = st.selectbox("Select a table", sorted(docs.keys()), key="doc_table_select")
        if selected_doc:
            doc = docs[selected_doc]
            st.subheader(f"`{selected_doc}`")
            st.markdown(f"**Business Summary**\n\n{doc.get('business_summary', 'N/A')}")

            st.subheader("Column Descriptions")
            col_descs = doc.get("column_descriptions", {})
            for col_name, desc in col_descs.items():
                st.markdown(f"- **`{col_name}`**: {desc}")

            related = doc.get("related_tables", [])
            if related:
                st.subheader("Related Tables")
                st.markdown(", ".join(f"`{t}`" for t in related))

            recs = doc.get("usage_recommendations", [])
            if recs:
                st.subheader("Usage Recommendations")
                for rec in recs:
                    st.markdown(f"- {rec}")

            queries = doc.get("suggested_queries", [])
            if queries:
                st.subheader("Suggested SQL Queries")
                for q in queries:
                    st.code(q, language="sql")


# ── Artifacts Tab ──────────────────────────────────────────────────────────

with tab_artifacts:
    st.header("Generated Artifacts")
    state = st.session_state.get("pipeline_state", {})
    artifact_paths = state.get("artifacts", [])

    if not artifact_paths:
        # Scan outputs dir
        artifact_paths = [str(p) for p in sorted(OUTPUTS_DIR.glob("*.*"))]

    if not artifact_paths:
        st.info("No artifacts generated yet. Run the pipeline first.")
    else:
        for art_path in artifact_paths:
            path = Path(art_path)
            if path.exists():
                col1, col2 = st.columns([4, 1])
                col1.markdown(f"**{path.name}** ({path.stat().st_size / 1024:.1f} KB)")
                with col2:
                    content = path.read_text(encoding="utf-8")
                    mime = "application/json" if path.suffix == ".json" else "text/markdown"
                    st.download_button(
                        label="Download",
                        data=content,
                        file_name=path.name,
                        mime=mime,
                        key=f"dl_{path.name}",
                    )
                if path.suffix == ".json":
                    with st.expander(f"Preview: {path.name}"):
                        st.json(json.loads(content)[:5] if isinstance(json.loads(content), list) else content[:2000])
