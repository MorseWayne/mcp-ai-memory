"""MCP server that provides local long-term memory with multiple LLM providers."""

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

from .config import create_mem0_client, DEFAULT_USER_ID
from .schemas import ToolMessage

load_dotenv()

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, log_level), format="%(levelname)s %(name)s | %(message)s")
logger = logging.getLogger("mcp_ai_memory")


@dataclass
class Mem0Context:
    """Context for the MCP server."""

    mem0_client: Memory


# Global singleton for Mem0 client to avoid multiple initializations in SSE mode
_mem0_client: Optional[Memory] = None
_mem0_lock: Optional[asyncio.Lock] = None


def _get_mem0_lock() -> asyncio.Lock:
    """Get or create the asyncio lock for Mem0 client initialization.
    
    asyncio.Lock must be created within an event loop context,
    so we lazily initialize it on first use.
    """
    global _mem0_lock
    if _mem0_lock is None:
        _mem0_lock = asyncio.Lock()
    return _mem0_lock


async def _get_or_create_mem0_client() -> Memory:
    """Get or create the singleton Mem0 client.
    
    Uses double-checked locking pattern with asyncio.Lock for async safety.
    Unlike threading.Lock, asyncio.Lock doesn't block the event loop.
    """
    global _mem0_client
    # Fast path: already initialized
    if _mem0_client is not None:
        return _mem0_client
    # Slow path: need to initialize with lock
    async with _get_mem0_lock():
        if _mem0_client is None:
            logger.info("Initializing Mem0 client...")
            _mem0_client = await asyncio.to_thread(create_mem0_client)
            logger.info("Mem0 client initialized successfully")
        return _mem0_client


@asynccontextmanager
async def mem0_lifespan(server: FastMCP) -> AsyncIterator[Mem0Context]:
    """Manage the Mem0 client lifecycle."""
    mem0_client = await _get_or_create_mem0_client()

    try:
        yield Mem0Context(mem0_client=mem0_client)
    finally:
        # Don't shutdown the client here as it's shared across connections
        pass


def create_server() -> FastMCP:
    """Create and configure the FastMCP server with all memory tools."""

    server = FastMCP(
        "ai-memory",
        instructions="MCP server for local long-term memory storage",
        lifespan=mem0_lifespan,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8050")),
    )

    def _get_client(ctx: Optional[Context]) -> Memory:
        """Extract Mem0 client from context.
        
        Args:
            ctx: The MCP context containing the Mem0 client.
            
        Returns:
            The Mem0 Memory client.
            
        Raises:
            RuntimeError: If context is None or invalid.
        """
        if ctx is None:
            raise RuntimeError("Context is required but got None")
        return ctx.request_context.lifespan_context.mem0_client

    def _safe_json(data: Any) -> str:
        """Safely convert data to JSON string."""
        try:
            return json.dumps(data, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": f"JSON serialization failed: {str(e)}"})

    def _extract_memories(result: Any) -> List[Dict[str, Any]]:
        """Extract memory list from Mem0 result."""
        if isinstance(result, dict) and "results" in result:
            return result["results"]
        if isinstance(result, list):
            return result
        return []

    def _build_scope_kwargs(
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        **extra: Any,
    ) -> Dict[str, Any]:
        """Build kwargs dict for Mem0 calls with scope filters.
        
        Args:
            user_id: User ID filter, defaults to DEFAULT_USER_ID if None.
            agent_id: Optional agent ID filter.
            run_id: Optional run ID filter.
            **extra: Additional keyword arguments to include.
            
        Returns:
            Dict with scope filters for Mem0 API calls.
        """
        kwargs: Dict[str, Any] = {"user_id": user_id or DEFAULT_USER_ID}
        if agent_id:
            kwargs["agent_id"] = agent_id
        if run_id:
            kwargs["run_id"] = run_id
        kwargs.update(extra)
        return kwargs

    def _analyze_add_result(result: Any, text: str, user_id: str) -> None:
        """Analyze and log the mem0 add result for debugging."""
        logger.debug(f"add_memory input text: {text[:200]}...")
        logger.debug(f"add_memory raw result: {result}")
        
        if isinstance(result, dict):
            # Check for 'results' key (standard mem0 response)
            results = result.get("results", [])
            if not results:
                logger.debug(
                    f"No memories extracted by LLM. Input: '{text[:100]}...' | "
                    f"This usually means the LLM did not find extractable facts/preferences."
                )
            else:
                for idx, mem in enumerate(results):
                    event = mem.get("event", "UNKNOWN")
                    memory_text = mem.get("memory", mem.get("text", "N/A"))
                    memory_id = mem.get("id", "N/A")
                    logger.debug(
                        f"Memory[{idx}] event={event}, id={memory_id}, "
                        f"text='{memory_text[:100]}...'"
                    )
                    if event == "NONE":
                        logger.debug(
                            f"Memory event=NONE means LLM decided not to store this. "
                            f"Possible reasons: duplicate, not a fact/preference, or LLM judgment."
                        )
            
            # Log any relations (for graph memory)
            relations = result.get("relations", [])
            if relations:
                logger.debug(f"Relations extracted: {relations}")
        else:
            logger.debug(f"Unexpected result type: {type(result)}")

    @server.tool(
        description="Store a new preference, fact, or conversation snippet in long-term memory."
    )
    async def add_memory(
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
        ctx: Optional[Context] = None,
    ) -> str:
        """Write durable information to local storage."""
        try:
            client = _get_client(ctx)
            conversation = (
                [ToolMessage(**msg).model_dump() for msg in messages]
                if messages
                else [{"role": "user", "content": text}]
            )
            kwargs = _build_scope_kwargs(user_id, agent_id, run_id)
            effective_user_id = kwargs["user_id"]
            if metadata:
                kwargs["metadata"] = metadata
            
            logger.debug(f"Calling mem0.add with conversation: {conversation}")
            # Run blocking call in thread pool for concurrency support
            result = await asyncio.to_thread(client.add, conversation, **kwargs)
            
            # Analyze the result for debugging
            _analyze_add_result(result, text, effective_user_id)
            
            # Count actual memories added
            added_count = 0
            if isinstance(result, dict) and "results" in result:
                added_count = sum(
                    1 for r in result.get("results", []) 
                    if r.get("event") == "ADD"
                )
            
            logger.info(
                f"Memory operation completed for user={effective_user_id}, "
                f"added={added_count} memories"
            )
            return _safe_json(result)
        except Exception as e:
            logger.error(f"Error adding memory: {e}", exc_info=True)
            return _safe_json({"error": str(e)})

    @server.tool(
        description="Semantic search across existing memories. Supports filtering by project via filters parameter."
    )
    async def search_memories(
        query: Annotated[str, Field(description="Natural language description of what to find.")],
        user_id: Annotated[Optional[str], Field(default=None, description="Filter by user ID.")] = None,
        agent_id: Annotated[Optional[str], Field(default=None, description="Filter by agent ID.")] = None,
        run_id: Annotated[Optional[str], Field(default=None, description="Filter by run ID.")] = None,
        filters: Annotated[
            Optional[Dict[str, Any]],
            Field(
                default=None,
                description="Metadata filters for search. Common usage: {'project': 'project-name'} to filter by project. Supports operators: exact match {'key': 'value'}, equals {'key': {'eq': 'value'}}, not equals {'key': {'ne': 'value'}}, in list {'key': {'in': ['val1', 'val2']}}.",
            ),
        ] = None,
        limit: Annotated[int, Field(default=100, description="Maximum number of results to return.")] = 100,
        ctx: Optional[Context] = None,
    ) -> str:
        """Semantic search against existing memories."""
        try:
            client = _get_client(ctx)
            kwargs = _build_scope_kwargs(user_id, agent_id, run_id, limit=limit)
            if filters:
                kwargs["filters"] = filters
            # Run blocking call in thread pool for concurrency support
            result = await asyncio.to_thread(client.search, query, **kwargs)
            memories = _extract_memories(result)
            logger.info(f"Search returned {len(memories)} results for query: {query[:50]}...")
            return _safe_json({"results": memories, "count": len(memories)})
        except Exception as e:
            logger.error(f"Error searching memories: {e}", exc_info=True)
            return _safe_json({"error": str(e)})

    @server.tool(
        description="List all memories with optional filters. Use for browsing stored memories."
    )
    async def get_memories(
        user_id: Annotated[Optional[str], Field(default=None, description="Filter by user ID.")] = None,
        agent_id: Annotated[Optional[str], Field(default=None, description="Filter by agent ID.")] = None,
        run_id: Annotated[Optional[str], Field(default=None, description="Filter by run ID.")] = None,
        ctx: Optional[Context] = None,
    ) -> str:
        """List memories via structured filters."""
        try:
            client = _get_client(ctx)
            kwargs = _build_scope_kwargs(user_id, agent_id, run_id)
            # Run blocking call in thread pool for concurrency support
            result = await asyncio.to_thread(client.get_all, **kwargs)
            memories = _extract_memories(result)
            logger.info(f"Retrieved {len(memories)} memories for user={kwargs.get('user_id')}")
            return _safe_json({"results": memories, "count": len(memories)})
        except Exception as e:
            logger.error(f"Error getting memories: {e}", exc_info=True)
            return _safe_json({"error": str(e)})

    @server.tool(description="Fetch a single memory by its memory_id.")
    async def get_memory(
        memory_id: Annotated[str, Field(description="Exact memory_id to fetch.")],
        ctx: Optional[Context] = None,
    ) -> str:
        """Retrieve a single memory once you know its ID."""
        try:
            client = _get_client(ctx)
            # Run blocking call in thread pool for concurrency support
            result = await asyncio.to_thread(client.get, memory_id)
            logger.info(f"Retrieved memory: {memory_id}")
            return _safe_json(result)
        except Exception as e:
            logger.error(f"Error getting memory {memory_id}: {e}", exc_info=True)
            return _safe_json({"error": str(e)})

    @server.tool(description="Overwrite an existing memory's text.")
    async def update_memory(
        memory_id: Annotated[str, Field(description="Exact memory_id to overwrite.")],
        text: Annotated[str, Field(description="Replacement text for the memory.")],
        ctx: Optional[Context] = None,
    ) -> str:
        """Overwrite an existing memory's text after confirming the exact memory_id."""
        try:
            client = _get_client(ctx)
            # Run blocking call in thread pool for concurrency support
            result = await asyncio.to_thread(client.update, memory_id=memory_id, data=text)
            logger.info(f"Updated memory: {memory_id}")
            return _safe_json(result)
        except Exception as e:
            logger.error(f"Error updating memory {memory_id}: {e}", exc_info=True)
            return _safe_json({"error": str(e)})

    @server.tool(description="Delete a single memory by its memory_id.")
    async def delete_memory(
        memory_id: Annotated[str, Field(description="Exact memory_id to delete.")],
        ctx: Optional[Context] = None,
    ) -> str:
        """Delete a single memory."""
        try:
            client = _get_client(ctx)
            # Run blocking call in thread pool for concurrency support
            result = await asyncio.to_thread(client.delete, memory_id=memory_id)
            logger.info(f"Deleted memory: {memory_id}")
            return _safe_json(result)
        except Exception as e:
            logger.error(f"Error deleting memory {memory_id}: {e}", exc_info=True)
            return _safe_json({"error": str(e)})

    @server.tool(description="Bulk delete memories by scope. WARNING: Due to a bug in mem0 1.0.x, this may delete ALL memories regardless of filters! Use with extreme caution.")
    async def delete_all_memories(
        user_id: Annotated[Optional[str], Field(default=None, description="User scope to delete.")] = None,
        agent_id: Annotated[Optional[str], Field(default=None, description="Agent scope to delete.")] = None,
        run_id: Annotated[Optional[str], Field(default=None, description="Run scope to delete.")] = None,
        ctx: Optional[Context] = None,
    ) -> str:
        """Delete multiple memories by scope.
        
        WARNING: Due to a known bug in mem0 1.0.x (see GitHub issue #3746),
        delete_all may ignore user_id/agent_id/run_id filters and delete ALL memories!
        Use delete_memory for safer individual deletions.
        """
        # Log warning about the known bug
        logger.warning(
            "delete_all_memories called. Due to mem0 1.0.x bug, this may delete ALL memories! "
            f"Requested filters: user_id={user_id}, agent_id={agent_id}, run_id={run_id}"
        )
        
        try:
            client = _get_client(ctx)
            kwargs: Dict[str, Any] = {}
            if user_id:
                kwargs["user_id"] = user_id
            if agent_id:
                kwargs["agent_id"] = agent_id
            if run_id:
                kwargs["run_id"] = run_id
            # Run blocking call in thread pool for concurrency support
            result = await asyncio.to_thread(client.delete_all, **kwargs)
            logger.info("Bulk delete executed")
            return _safe_json(result)
        except Exception as e:
            logger.error(f"Error bulk deleting memories: {e}", exc_info=True)
            return _safe_json({"error": str(e)})

    @server.tool(description="View change history for a memory.")
    async def get_memory_history(
        memory_id: Annotated[str, Field(description="Memory ID to get history for.")],
        ctx: Optional[Context] = None,
    ) -> str:
        """Get change history for a memory."""
        try:
            client = _get_client(ctx)
            # Run blocking call in thread pool for concurrency support
            result = await asyncio.to_thread(client.get_history, memory_id=memory_id)
            logger.info(f"History fetched for memory: {memory_id}")
            return _safe_json(result)
        except Exception as e:
            logger.error(f"Error getting memory history {memory_id}: {e}", exc_info=True)
            return _safe_json({"error": str(e)})

    @server.tool(description="Reset all memories. Use with caution!")
    async def reset_memories(ctx: Optional[Context] = None) -> str:
        """Reset all stored memories."""
        try:
            client = _get_client(ctx)
            # Run blocking call in thread pool for concurrency support
            result = await asyncio.to_thread(client.reset)
            logger.warning("All memories have been reset")
            return _safe_json(result)
        except Exception as e:
            logger.error(f"Error resetting memories: {e}", exc_info=True)
            return _safe_json({"error": str(e)})

    @server.prompt()
    def memory_assistant() -> str:
        """Get help with memory operations and best practices."""
        return """You are using the AI Memory MCP server for long-term memory management.

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

    logger.info(f"Starting AI Memory MCP server (transport={transport}, user={DEFAULT_USER_ID})")

    if transport == "streamable-http":
        # Streamable HTTP: stateless, better reconnection handling
        # Default path is /mcp
        await server.run_streamable_http_async()
    elif transport == "sse":
        # Legacy SSE mode (deprecated in MCP spec 2025-03-26)
        await server.run_sse_async()
    else:
        await server.run_stdio_async()


def main() -> None:
    """Run the MCP server."""
    try:
        asyncio.run(run_async())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")


if __name__ == "__main__":
    main()
