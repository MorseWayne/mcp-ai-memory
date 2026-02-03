"""MCP server that provides local Mem0 memory storage with custom LLM providers."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated, Any, Dict, List, Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import Context, FastMCP
from mem0 import Memory
from pydantic import Field

try:
    from .config import create_mem0_client, DEFAULT_USER_ID
    from .schemas import ToolMessage
except ImportError:
    from config import create_mem0_client, DEFAULT_USER_ID
    from schemas import ToolMessage

load_dotenv()

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, log_level), format="%(levelname)s %(name)s | %(message)s")
logger = logging.getLogger("mem0_local_mcp")


@dataclass
class Mem0Context:
    """Context for the Mem0 MCP server."""

    mem0_client: Memory


@asynccontextmanager
async def mem0_lifespan(server: FastMCP) -> AsyncIterator[Mem0Context]:
    """Manage the Mem0 client lifecycle.

    Args:
        server: The FastMCP server instance

    Yields:
        Mem0Context: The context containing the Mem0 client
    """
    logger.info("Initializing Mem0 client...")
    mem0_client = create_mem0_client()
    logger.info("Mem0 client initialized successfully")

    try:
        yield Mem0Context(mem0_client=mem0_client)
    finally:
        logger.info("Shutting down Mem0 client...")


def create_server() -> FastMCP:
    """Create and configure the FastMCP server with all memory tools."""

    server = FastMCP(
        "mem0-local",
        description="MCP server for local long-term memory storage with Mem0",
        lifespan=mem0_lifespan,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8050")),
    )

    def _get_client(ctx: Context) -> Memory:
        """Extract Mem0 client from context."""
        return ctx.request_context.lifespan_context.mem0_client

    def _safe_json(data: Any) -> str:
        """Safely convert data to JSON string."""
        try:
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": f"JSON serialization failed: {str(e)}"})

    def _extract_memories(result: Any) -> List[Dict[str, Any]]:
        """Extract memory list from Mem0 result."""
        if isinstance(result, dict) and "results" in result:
            return result["results"]
        if isinstance(result, list):
            return result
        return []

    # =========================================================================
    # Tool: add_memory
    # =========================================================================
    @server.tool(
        description="Store a new preference, fact, or conversation snippet in long-term memory."
    )
    def add_memory(
        text: Annotated[
            str,
            Field(description="Plain sentence summarizing what to store. Required."),
        ],
        messages: Annotated[
            Optional[List[Dict[str, str]]],
            Field(
                default=None,
                description="Structured conversation history with 'role'/'content'. Use when you have multiple turns.",
            ),
        ] = None,
        user_id: Annotated[
            Optional[str],
            Field(default=None, description="Override the default user scope for this write."),
        ] = None,
        agent_id: Annotated[
            Optional[str],
            Field(default=None, description="Optional agent identifier."),
        ] = None,
        run_id: Annotated[
            Optional[str],
            Field(default=None, description="Optional run identifier."),
        ] = None,
        metadata: Annotated[
            Optional[Dict[str, Any]],
            Field(default=None, description="Attach arbitrary metadata JSON to the memory."),
        ] = None,
        ctx: Context = None,
    ) -> str:
        """Write durable information to Mem0 local storage."""
        try:
            client = _get_client(ctx)

            # Build the conversation content
            if messages:
                conversation = [ToolMessage(**msg).model_dump() for msg in messages]
            else:
                conversation = [{"role": "user", "content": text}]

            # Build kwargs
            kwargs: Dict[str, Any] = {}
            kwargs["user_id"] = user_id or DEFAULT_USER_ID
            if agent_id:
                kwargs["agent_id"] = agent_id
            if run_id:
                kwargs["run_id"] = run_id
            if metadata:
                kwargs["metadata"] = metadata

            result = client.add(conversation, **kwargs)
            logger.info(f"Memory added for user={kwargs.get('user_id')}")
            return _safe_json(result)

        except Exception as e:
            logger.error(f"Error adding memory: {e}")
            return _safe_json({"error": str(e)})

    # =========================================================================
    # Tool: search_memories
    # =========================================================================
    @server.tool(
        description="""Semantic search across existing memories.
        
        Use this to find relevant information from stored memories.
        Results are ranked by semantic relevance to the query."""
    )
    def search_memories(
        query: Annotated[
            str,
            Field(description="Natural language description of what to find."),
        ],
        user_id: Annotated[
            Optional[str],
            Field(default=None, description="Filter by user ID. Defaults to the configured user."),
        ] = None,
        agent_id: Annotated[
            Optional[str],
            Field(default=None, description="Filter by agent ID."),
        ] = None,
        run_id: Annotated[
            Optional[str],
            Field(default=None, description="Filter by run ID."),
        ] = None,
        limit: Annotated[
            int,
            Field(default=10, description="Maximum number of results to return."),
        ] = 10,
        ctx: Context = None,
    ) -> str:
        """Semantic search against existing memories."""
        try:
            client = _get_client(ctx)

            kwargs: Dict[str, Any] = {"limit": limit}
            kwargs["user_id"] = user_id or DEFAULT_USER_ID
            if agent_id:
                kwargs["agent_id"] = agent_id
            if run_id:
                kwargs["run_id"] = run_id

            result = client.search(query, **kwargs)
            memories = _extract_memories(result)

            logger.info(f"Search returned {len(memories)} results for query: {query[:50]}...")
            return _safe_json({"results": memories, "count": len(memories)})

        except Exception as e:
            logger.error(f"Error searching memories: {e}")
            return _safe_json({"error": str(e)})

    # =========================================================================
    # Tool: get_memories
    # =========================================================================
    @server.tool(
        description="List all memories with optional filters. Use for browsing stored memories."
    )
    def get_memories(
        user_id: Annotated[
            Optional[str],
            Field(default=None, description="Filter by user ID. Defaults to the configured user."),
        ] = None,
        agent_id: Annotated[
            Optional[str],
            Field(default=None, description="Filter by agent ID."),
        ] = None,
        run_id: Annotated[
            Optional[str],
            Field(default=None, description="Filter by run ID."),
        ] = None,
        ctx: Context = None,
    ) -> str:
        """List memories via structured filters."""
        try:
            client = _get_client(ctx)

            kwargs: Dict[str, Any] = {}
            kwargs["user_id"] = user_id or DEFAULT_USER_ID
            if agent_id:
                kwargs["agent_id"] = agent_id
            if run_id:
                kwargs["run_id"] = run_id

            result = client.get_all(**kwargs)
            memories = _extract_memories(result)

            logger.info(f"Retrieved {len(memories)} memories for user={kwargs.get('user_id')}")
            return _safe_json({"results": memories, "count": len(memories)})

        except Exception as e:
            logger.error(f"Error getting memories: {e}")
            return _safe_json({"error": str(e)})

    # =========================================================================
    # Tool: get_memory
    # =========================================================================
    @server.tool(description="Fetch a single memory by its memory_id.")
    def get_memory(
        memory_id: Annotated[
            str,
            Field(description="Exact memory_id to fetch."),
        ],
        ctx: Context = None,
    ) -> str:
        """Retrieve a single memory once you know its ID."""
        try:
            client = _get_client(ctx)
            result = client.get(memory_id)
            logger.info(f"Retrieved memory: {memory_id}")
            return _safe_json(result)

        except Exception as e:
            logger.error(f"Error getting memory {memory_id}: {e}")
            return _safe_json({"error": str(e)})

    # =========================================================================
    # Tool: update_memory
    # =========================================================================
    @server.tool(description="Overwrite an existing memory's text.")
    def update_memory(
        memory_id: Annotated[
            str,
            Field(description="Exact memory_id to overwrite."),
        ],
        text: Annotated[
            str,
            Field(description="Replacement text for the memory."),
        ],
        ctx: Context = None,
    ) -> str:
        """Overwrite an existing memory's text after confirming the exact memory_id."""
        try:
            client = _get_client(ctx)
            result = client.update(memory_id=memory_id, data=text)
            logger.info(f"Updated memory: {memory_id}")
            return _safe_json(result)

        except Exception as e:
            logger.error(f"Error updating memory {memory_id}: {e}")
            return _safe_json({"error": str(e)})

    # =========================================================================
    # Tool: delete_memory
    # =========================================================================
    @server.tool(description="Delete a single memory by its memory_id.")
    def delete_memory(
        memory_id: Annotated[
            str,
            Field(description="Exact memory_id to delete."),
        ],
        ctx: Context = None,
    ) -> str:
        """Delete a memory once you confirm the memory_id to remove."""
        try:
            client = _get_client(ctx)
            result = client.delete(memory_id)
            logger.info(f"Deleted memory: {memory_id}")
            return _safe_json({"success": True, "deleted_id": memory_id, "result": result})

        except Exception as e:
            logger.error(f"Error deleting memory {memory_id}: {e}")
            return _safe_json({"error": str(e)})

    # =========================================================================
    # Tool: delete_all_memories
    # =========================================================================
    @server.tool(
        description="Bulk delete all memories in the given user/agent/run scope."
    )
    def delete_all_memories(
        user_id: Annotated[
            Optional[str],
            Field(default=None, description="User scope to delete; defaults to server user."),
        ] = None,
        agent_id: Annotated[
            Optional[str],
            Field(default=None, description="Optional agent scope to delete."),
        ] = None,
        run_id: Annotated[
            Optional[str],
            Field(default=None, description="Optional run scope to delete."),
        ] = None,
        ctx: Context = None,
    ) -> str:
        """Bulk-delete every memory in the confirmed scope."""
        try:
            client = _get_client(ctx)

            kwargs: Dict[str, Any] = {}
            kwargs["user_id"] = user_id or DEFAULT_USER_ID
            if agent_id:
                kwargs["agent_id"] = agent_id
            if run_id:
                kwargs["run_id"] = run_id

            result = client.delete_all(**kwargs)
            logger.info(f"Deleted all memories for scope: {kwargs}")
            return _safe_json({"success": True, "scope": kwargs, "result": result})

        except Exception as e:
            logger.error(f"Error deleting all memories: {e}")
            return _safe_json({"error": str(e)})

    # =========================================================================
    # Tool: get_memory_history
    # =========================================================================
    @server.tool(description="Get the history of changes for a specific memory.")
    def get_memory_history(
        memory_id: Annotated[
            str,
            Field(description="Memory ID to get history for."),
        ],
        ctx: Context = None,
    ) -> str:
        """Retrieve the history of a memory showing how it has changed over time."""
        try:
            client = _get_client(ctx)
            result = client.history(memory_id)
            logger.info(f"Retrieved history for memory: {memory_id}")
            return _safe_json(result)

        except Exception as e:
            logger.error(f"Error getting memory history {memory_id}: {e}")
            return _safe_json({"error": str(e)})

    # =========================================================================
    # Tool: reset_memories
    # =========================================================================
    @server.tool(
        description="Reset/clear all memories in the database. Use with caution!"
    )
    def reset_memories(
        confirm: Annotated[
            bool,
            Field(description="Must be True to confirm the reset operation."),
        ] = False,
        ctx: Context = None,
    ) -> str:
        """Reset all memories. Requires explicit confirmation."""
        if not confirm:
            return _safe_json({
                "error": "confirmation_required",
                "message": "Set confirm=True to proceed with reset. This will delete ALL memories!"
            })

        try:
            client = _get_client(ctx)
            result = client.reset()
            logger.warning("All memories have been reset!")
            return _safe_json({"success": True, "message": "All memories have been reset", "result": result})

        except Exception as e:
            logger.error(f"Error resetting memories: {e}")
            return _safe_json({"error": str(e)})

    # =========================================================================
    # Prompt: memory_assistant
    # =========================================================================
    @server.prompt()
    def memory_assistant() -> str:
        """Get help with memory operations and best practices."""
        return """You are using the Mem0 Local MCP server for long-term memory management.

Quick Start:
1. Store memories: Use add_memory to save facts, preferences, or conversations
2. Search memories: Use search_memories for semantic queries
3. List memories: Use get_memories for browsing all stored memories
4. Update/Delete: Use update_memory and delete_memory for modifications
5. History: Use get_memory_history to see how a memory changed over time

Available Tools:
- add_memory: Store new information (text or conversation)
- search_memories: Find memories by meaning (semantic search)
- get_memories: List all memories with optional filters
- get_memory: Get a single memory by ID
- update_memory: Update an existing memory's content
- delete_memory: Delete a single memory
- delete_all_memories: Bulk delete memories by scope
- get_memory_history: View change history for a memory
- reset_memories: Clear all memories (use with caution!)

Tips:
- Memories are automatically indexed for semantic search
- Use user_id to separate memories by user
- Use agent_id and run_id for more granular organization
- Search returns results ranked by relevance"""

    return server


async def run_async():
    """Run the MCP server asynchronously."""
    server = create_server()
    transport = os.getenv("TRANSPORT", "sse")

    logger.info(f"Starting Mem0 Local MCP server (transport={transport}, user={DEFAULT_USER_ID})")

    if transport == "sse":
        await server.run_sse_async()
    else:
        await server.run_stdio_async()


def main() -> None:
    """Run the MCP server."""
    asyncio.run(run_async())


if __name__ == "__main__":
    main()
