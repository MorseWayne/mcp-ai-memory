"""Mem0 Local MCP Server - Local memory storage with custom LLM providers."""

from .server import create_server, main
from .config import create_mem0_client, DEFAULT_USER_ID

__version__ = "0.1.0"
__all__ = ["create_server", "main", "create_mem0_client", "DEFAULT_USER_ID"]
