"""
Neuro-Fabric CLI Entry Point.

Runs the full documentation pipeline from the command line:
  schema extraction → quality analysis → AI documentation → export

Usage:
    python main.py                         # use Supabase default config
    python main.py --name mydb             # custom DB name for artifacts
    python main.py --url "postgresql://..."  # custom connection URL
    python main.py --chat                  # interactive CLI chat mode
    python main.py --schema-only           # only extract schema
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from core.config import LOG_LEVEL, validate_config

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("neuro-fabric")


def _print_banner():
    print("""
╔═══════════════════════════════════════════╗
║          🧠  N E U R O - F A B R I C      ║
║   AI-Powered Enterprise Data Dictionary   ║
╚═══════════════════════════════════════════╝
""")


def run_pipeline(db_config: dict, schema_only: bool = False):
    """Run the full documentation pipeline synchronously."""
    from agents.supervisor import get_pipeline_app

    app = get_pipeline_app()

    stages = ["Schema Extraction", "Quality Analysis", "AI Documentation", "Export"]
    if schema_only:
        stages = ["Schema Extraction"]

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

    print(f"Starting pipeline for database: '{db_config.get('name', 'database')}'")
    print(f"Stages: {' → '.join(stages)}\n")

    final_state = None
    last_stage = ""

    for event in app.stream(initial_state, stream_mode="values"):
        final_state = event

        schema_done = bool(event.get("schema"))
        quality_done = bool(event.get("quality_report"))
        docs_done = bool(event.get("documentation"))
        artifacts_done = bool(event.get("artifacts"))

        current_stage = ""
        if artifacts_done:
            current_stage = "Export"
        elif docs_done:
            current_stage = "AI Documentation"
        elif quality_done:
            current_stage = "Quality Analysis"
        elif schema_done:
            current_stage = "Schema Extraction"

        if current_stage and current_stage != last_stage:
            print(f"  ✓ {current_stage} complete")
            last_stage = current_stage

        if schema_only and schema_done:
            break

        for err in event.get("errors", []):
            print(f"  ⚠ Warning: {err}", file=sys.stderr)

    return final_state


def run_chat_mode(db_config: dict, pipeline_state: dict):
    """Run an interactive CLI chat session."""
    from langchain_core.messages import HumanMessage
    from agents.supervisor import get_chat_app

    chat_app = get_chat_app()
    import uuid
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    print("\n━━━ Chat Mode ━━━")
    print("Ask questions about your database schema. Type 'exit' to quit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting chat.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            print("Goodbye!")
            break

        chat_input = {
            "messages": [HumanMessage(content=user_input)],
            "db_config": db_config,
            "schema": pipeline_state.get("schema", {}),
            "quality_report": pipeline_state.get("quality_report", {}),
            "documentation": pipeline_state.get("documentation", {}),
            "artifacts": pipeline_state.get("artifacts", []),
            "current_task": "chat",
            "errors": [],
        }

        try:
            result = chat_app.invoke(chat_input, config=config)
            ai_messages = result.get("messages", [])
            response = ai_messages[-1].content if ai_messages else "(no response)"
            print(f"\nAssistant: {response}\n")
        except Exception as e:
            print(f"Error: {e}\n", file=sys.stderr)


def print_summary(final_state: dict):
    """Print a human-readable pipeline summary."""
    if not final_state:
        print("Pipeline produced no output.")
        return

    schema = final_state.get("schema", {})
    quality = final_state.get("quality_report", {})
    docs = final_state.get("documentation", {})
    artifacts = final_state.get("artifacts", [])
    errors = final_state.get("errors", [])

    print("\n" + "━" * 50)
    print("Pipeline Summary")
    print("━" * 50)
    print(f"  Tables extracted:    {len(schema)}")
    print(f"  Tables with quality: {len(quality)}")
    print(f"  Tables documented:   {len(docs)}")
    print(f"  Artifacts generated: {len(artifacts)}")

    if artifacts:
        print("\nArtifacts:")
        for art in artifacts:
            size_kb = Path(art).stat().st_size / 1024 if Path(art).exists() else 0
            print(f"  → {art} ({size_kb:.1f} KB)")

    if errors:
        print(f"\nWarnings ({len(errors)}):")
        for err in errors:
            print(f"  ⚠ {err}")


def main():
    _print_banner()

    parser = argparse.ArgumentParser(
        description="Neuro-Fabric: AI-Powered Enterprise Data Dictionary"
    )
    parser.add_argument("--name", default="database", help="Database/project name for artifacts")
    parser.add_argument("--url", default="", help="Database connection URL (overrides env)")
    parser.add_argument("--chat", action="store_true", help="Launch interactive CLI chat after pipeline")
    parser.add_argument("--schema-only", action="store_true", help="Only run schema extraction stage")
    parser.add_argument("--chat-only", action="store_true", help="Skip pipeline, go straight to chat")
    args = parser.parse_args()

    # Config validation
    missing = validate_config()
    if missing:
        print(f"⚠ Missing required environment variables: {', '.join(missing)}", file=sys.stderr)
        print("  Copy .env.example to .env and fill in your credentials.\n", file=sys.stderr)
        if not args.chat_only:
            sys.exit(1)

    db_config = {
        "url": args.url,
        "name": args.name,
    }

    pipeline_state: dict = {}

    if not args.chat_only:
        try:
            pipeline_state = run_pipeline(db_config, schema_only=args.schema_only) or {}
            print_summary(pipeline_state)
        except KeyboardInterrupt:
            print("\nPipeline interrupted.")
            sys.exit(0)
        except Exception as e:
            print(f"Pipeline failed: {e}", file=sys.stderr)
            logger.exception("Pipeline error")
            sys.exit(1)

    if args.chat or args.chat_only:
        run_chat_mode(db_config, pipeline_state)


if __name__ == "__main__":
    main()
