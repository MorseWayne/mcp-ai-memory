"""AI Memory MCP Server - Local long-term memory with multiple LLM providers."""

from importlib.metadata import version, PackageNotFoundError

# Lazy imports to avoid circular import issues when running with python -m
def __getattr__(name: str):
    if name == "create_server":
        from .server import create_server
        return create_server
    elif name == "main":
        from .server import main
        return main
    elif name == "create_mem0_client":
        from .config import create_mem0_client
        return create_mem0_client
    elif name == "DEFAULT_USER_ID":
        from .config import DEFAULT_USER_ID
        return DEFAULT_USER_ID
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

from .config import DEFAULT_USER_ID

try:
    __version__ = version("mcp-ai-memory")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"  # Development mode

__all__ = ["create_server", "main", "create_mem0_client", "DEFAULT_USER_ID", "__version__"]
