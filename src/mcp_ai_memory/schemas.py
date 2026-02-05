"""Pydantic models for the AI Memory MCP server."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ToolMessage(BaseModel):
    """A single message in a conversation."""

    role: str = Field(..., description="Role of the speaker, e.g., 'user' or 'assistant'.")
    content: str = Field(..., description="Full text of the utterance to store.")
