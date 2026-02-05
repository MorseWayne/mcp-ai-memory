"""AI Memory MCP Server - Local long-term memory with multiple LLM providers."""

from importlib.metadata import version, PackageNotFoundError

from .server import create_server, main
from .config import create_mem0_client, DEFAULT_USER_ID

try:
    __version__ = version("mcp-ai-memory")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"  # Development mode

__all__ = ["create_server", "main", "create_mem0_client", "DEFAULT_USER_ID", "__version__"]
