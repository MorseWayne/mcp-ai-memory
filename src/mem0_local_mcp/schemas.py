"""Pydantic models for the Mem0 Local MCP server."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ToolMessage(BaseModel):
    """A single message in a conversation."""

    role: str = Field(..., description="Role of the speaker, e.g., 'user' or 'assistant'.")
    content: str = Field(..., description="Full text of the utterance to store.")


class AddMemoryArgs(BaseModel):
    """Arguments for adding a memory."""

    text: Optional[str] = Field(
        None,
        description="Simple sentence to remember; converted into a user message when set.",
    )
    messages: Optional[List[ToolMessage]] = Field(
        None,
        description="Explicit role/content history for durable storage. Provide this OR `text`.",
    )
    user_id: Optional[str] = Field(None, description="Override for the user ID.")
    agent_id: Optional[str] = Field(None, description="Optional agent identifier.")
    run_id: Optional[str] = Field(None, description="Optional run identifier.")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Opaque metadata to persist.")


class SearchMemoriesArgs(BaseModel):
    """Arguments for searching memories."""

    query: str = Field(..., description="Describe what you want to find.")
    user_id: Optional[str] = Field(None, description="Filter by user ID.")
    agent_id: Optional[str] = Field(None, description="Filter by agent ID.")
    run_id: Optional[str] = Field(None, description="Filter by run ID.")
    limit: Optional[int] = Field(None, description="Maximum number of matches (default: 10).")


class GetMemoriesArgs(BaseModel):
    """Arguments for listing memories."""

    user_id: Optional[str] = Field(None, description="Filter by user ID.")
    agent_id: Optional[str] = Field(None, description="Filter by agent ID.")
    run_id: Optional[str] = Field(None, description="Filter by run ID.")


class UpdateMemoryArgs(BaseModel):
    """Arguments for updating a memory."""

    memory_id: str = Field(..., description="Exact memory_id to update.")
    text: str = Field(..., description="New text content for the memory.")


class DeleteMemoryArgs(BaseModel):
    """Arguments for deleting a memory."""

    memory_id: str = Field(..., description="Exact memory_id to delete.")


class DeleteAllArgs(BaseModel):
    """Arguments for bulk deleting memories."""

    user_id: Optional[str] = Field(None, description="User scope to delete.")
    agent_id: Optional[str] = Field(None, description="Agent scope to delete.")
    run_id: Optional[str] = Field(None, description="Run scope to delete.")


class MemoryHistoryArgs(BaseModel):
    """Arguments for getting memory history."""

    memory_id: str = Field(..., description="Memory ID to get history for.")
