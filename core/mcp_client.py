"""
Supabase MCP client setup using langchain-mcp-adapters.

The MultiServerMCPClient spawns the Supabase MCP server as a subprocess
(via npx) and exposes its tools as LangChain-compatible tool objects.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from langchain_mcp_adapters.client import MultiServerMCPClient

from core.config import SUPABASE_PAT, SUPABASE_URL

logger = logging.getLogger(__name__)

_MCP_SERVER_CONFIG = {
    "supabase": {
        "command": "npx",
        "args": [
            "-y",
            "@supabase/mcp-server-supabase@latest",
            "--access-token",
            SUPABASE_PAT,
            "--project-ref",
            # Extract project ref from URL: https://<ref>.supabase.co
            SUPABASE_URL.replace("https://", "").split(".")[0] if SUPABASE_URL else "",
        ],
        "transport": "stdio",
    }
}


@asynccontextmanager
async def get_mcp_client() -> AsyncGenerator[MultiServerMCPClient, None]:
    """Context manager that yields a connected MultiServerMCPClient."""
    if not SUPABASE_PAT:
        raise ValueError(
            "SUPABASE_PAT is required for the Supabase MCP server. "
            "Set it in your .env file."
        )

    logger.info("Starting Supabase MCP server...")
    async with MultiServerMCPClient(_MCP_SERVER_CONFIG) as client:
        logger.info("Supabase MCP server connected.")
        yield client


async def get_mcp_tools() -> list:
    """
    Return the list of LangChain tools exposed by the Supabase MCP server.
    Intended for short-lived tool discovery; prefer get_mcp_client() for
    long-running operations.
    """
    async with get_mcp_client() as client:
        tools = client.get_tools()
        logger.info("Discovered %d MCP tools from Supabase.", len(tools))
        return tools
