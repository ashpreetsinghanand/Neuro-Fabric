"""
Supervisor Agent and LangGraph Pipeline.

Orchestrates all specialist agents using LangGraph's StateGraph with a
supervisor node that routes tasks to the right specialist based on the
current state and user intent.

Pipeline modes:
  1. FULL PIPELINE: schema → quality → ai_docs → export
  2. CHAT mode: routes user messages to the chat agent

The supervisor is also used for chat-driven requests, where it decides
whether to re-run specific agents (e.g. re-extract schema after a
schema change alert) or simply answer via the chat agent.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from agents.ai_doc_agent import ai_doc_agent_node
from agents.chat_agent import chat_agent_node
from agents.export_agent import export_agent_node
from agents.quality_agent import quality_agent_node
from agents.schema_agent import schema_agent_node
from core.config import GEMINI_MODEL, GOOGLE_API_KEY
from core.state import AgentState, extract_message_content

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Node: supervisor_router
# Decides the next step based on current state in the FULL pipeline.
# ---------------------------------------------------------------------------

def _pipeline_router(state: AgentState) -> Literal[
    "schema_agent", "quality_agent", "ai_doc_agent", "export_agent", "chat_agent", "__end__"
]:
    """
    Deterministic router for the full documentation pipeline.
    Advances through stages sequentially based on what state is populated.
    """
    current_task = state.get("current_task", "pipeline")

    # Chat mode: route directly to chat agent
    if current_task == "chat":
        return "chat_agent"

    schema = state.get("schema", {})
    quality = state.get("quality_report", {})
    docs = state.get("documentation", {})
    artifacts = state.get("artifacts", [])

    # Stage 1: Schema extraction
    if not schema:
        return "schema_agent"

    # Stage 2: Quality analysis
    if not quality:
        return "quality_agent"

    # Stage 3: AI documentation
    if not docs:
        return "ai_doc_agent"

    # Stage 4: Export artifacts
    if not artifacts:
        return "export_agent"

    # All done
    return "__end__"


# ---------------------------------------------------------------------------
# Node: supervisor_node (LLM-powered for chat routing decisions)
# ---------------------------------------------------------------------------

_SUPERVISOR_SYSTEM = """You are the Supervisor Agent for Neuro-Fabric, an AI-powered data dictionary platform.

You coordinate a team of specialist agents:
- schema_agent: Extracts table/column metadata from the database
- quality_agent: Analyzes data quality (null rates, statistics, freshness, PK health)
- ai_doc_agent: Generates business-friendly documentation using Gemini AI
- export_agent: Writes artifacts (JSON + Markdown) to disk
- chat_agent: Answers natural language questions about the database

Your job is to decide which agent should handle the current request.

Respond with ONLY one of these exact strings (no explanation):
schema_agent | quality_agent | ai_doc_agent | export_agent | chat_agent | FINISH
"""


def supervisor_node(state: AgentState) -> dict[str, Any]:
    """
    LLM-powered supervisor node for intelligent routing.
    Used primarily for dynamic/chat-driven pipeline decisions.
    """
    current_task = state.get("current_task", "pipeline")

    # For the deterministic pipeline, skip LLM overhead
    if current_task == "pipeline":
        return {}  # routing handled by _pipeline_router

    # For chat/dynamic mode, use LLM to decide
    llm = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GOOGLE_API_KEY,
        temperature=0,
    )

    schema_populated = "yes" if state.get("schema") else "no"
    quality_populated = "yes" if state.get("quality_report") else "no"
    docs_populated = "yes" if state.get("documentation") else "no"

    context = (
        f"Current state:\n"
        f"- Schema extracted: {schema_populated}\n"
        f"- Quality analyzed: {quality_populated}\n"
        f"- Documentation generated: {docs_populated}\n"
        f"- Current task: {current_task}\n\n"
        f"Latest user message: {state.get('messages', [{}])[-1]}"
    )

    response = llm.invoke([
        SystemMessage(content=_SUPERVISOR_SYSTEM),
        HumanMessage(content=context),
    ])
    response_content = extract_message_content(response.content)
    decision = response_content.strip()
    logger.info("Supervisor decision: %s", decision)
    return {"current_task": decision if decision != "FINISH" else "done"}


# ---------------------------------------------------------------------------
# Build the pipeline graph (FULL documentation pipeline)
# ---------------------------------------------------------------------------

def build_pipeline_graph() -> StateGraph:
    """
    Build the full documentation pipeline graph:
    START → supervisor_router → [schema|quality|ai_doc|export] → END
    """
    graph = StateGraph(AgentState)

    # Add all specialist nodes
    graph.add_node("schema_agent", schema_agent_node)
    graph.add_node("quality_agent", quality_agent_node)
    graph.add_node("ai_doc_agent", ai_doc_agent_node)
    graph.add_node("export_agent", export_agent_node)
    graph.add_node("chat_agent", chat_agent_node)

    # Entry: START always goes to the router
    graph.add_conditional_edges(
        START,
        _pipeline_router,
        {
            "schema_agent": "schema_agent",
            "quality_agent": "quality_agent",
            "ai_doc_agent": "ai_doc_agent",
            "export_agent": "export_agent",
            "chat_agent": "chat_agent",
            "__end__": END,
        },
    )

    # After each agent, loop back to the router to decide next step
    for node in ["schema_agent", "quality_agent", "ai_doc_agent", "export_agent"]:
        graph.add_conditional_edges(
            node,
            _pipeline_router,
            {
                "schema_agent": "schema_agent",
                "quality_agent": "quality_agent",
                "ai_doc_agent": "ai_doc_agent",
                "export_agent": "export_agent",
                "chat_agent": "chat_agent",
                "__end__": END,
            },
        )

    # Chat agent always ends (one response per turn)
    graph.add_edge("chat_agent", END)

    return graph


# ---------------------------------------------------------------------------
# Build the chat graph (conversational mode with persistent state)
# ---------------------------------------------------------------------------

def build_chat_graph() -> StateGraph:
    """
    Lightweight graph for conversational chat mode.
    Only involves the chat_agent node, but can escalate to other agents.
    """
    graph = StateGraph(AgentState)

    graph.add_node("supervisor", supervisor_node)
    graph.add_node("schema_agent", schema_agent_node)
    graph.add_node("quality_agent", quality_agent_node)
    graph.add_node("ai_doc_agent", ai_doc_agent_node)
    graph.add_node("export_agent", export_agent_node)
    graph.add_node("chat_agent", chat_agent_node)

    graph.add_edge(START, "supervisor")

    def chat_supervisor_router(state: AgentState) -> str:
        task = state.get("current_task", "chat")
        routing = {
            "schema_agent": "schema_agent",
            "quality_agent": "quality_agent",
            "ai_doc_agent": "ai_doc_agent",
            "export_agent": "export_agent",
            "chat_agent": "chat_agent",
            "done": END,
            "chat": "chat_agent",
            "pipeline": "schema_agent",
        }
        return routing.get(task, "chat_agent")

    graph.add_conditional_edges(
        "supervisor",
        chat_supervisor_router,
        {
            "schema_agent": "schema_agent",
            "quality_agent": "quality_agent",
            "ai_doc_agent": "ai_doc_agent",
            "export_agent": "export_agent",
            "chat_agent": "chat_agent",
            END: END,
        },
    )

    # After specialist agents, go back to chat
    for node in ["schema_agent", "quality_agent", "ai_doc_agent", "export_agent"]:
        graph.add_edge(node, "chat_agent")

    graph.add_edge("chat_agent", END)

    return graph


# ---------------------------------------------------------------------------
# Compiled graphs (singletons, compiled once at import time)
# ---------------------------------------------------------------------------

def get_pipeline_app():
    """Return a compiled pipeline app (full documentation run)."""
    return build_pipeline_graph().compile()


def get_chat_app():
    """Return a compiled chat app (conversational mode with memory)."""
    from langgraph.checkpoint.memory import MemorySaver
    memory = MemorySaver()
    return build_chat_graph().compile(checkpointer=memory)
