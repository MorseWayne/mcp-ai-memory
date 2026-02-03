"""Configuration and Mem0 client initialization for the local MCP server."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from mem0 import Memory

logger = logging.getLogger("mem0_local_mcp")


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable with optional default."""
    return os.getenv(key, default)


def get_env_bool(key: str, default: bool = False) -> bool:
    """Get boolean environment variable."""
    value = os.getenv(key, "").lower()
    if value in ("1", "true", "yes", "on"):
        return True
    if value in ("0", "false", "no", "off"):
        return False
    return default


def get_env_int(key: str, default: int) -> int:
    """Get integer environment variable."""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def get_env_float(key: str, default: float) -> float:
    """Get float environment variable."""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _build_llm_config() -> Dict[str, Any]:
    """Build LLM configuration from environment variables."""
    provider = get_env("LLM_PROVIDER", "openai")
    model = get_env("LLM_MODEL", "gpt-4o-mini")
    api_key = get_env("LLM_API_KEY")
    base_url = get_env("LLM_BASE_URL")
    temperature = get_env_float("LLM_TEMPERATURE", 0.2)
    max_tokens = get_env_int("LLM_MAX_TOKENS", 2000)

    config: Dict[str, Any] = {
        "provider": provider,
        "config": {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
    }

    # Provider-specific configurations
    if provider == "openai":
        if api_key:
            config["config"]["api_key"] = api_key
        if base_url:
            config["config"]["openai_base_url"] = base_url

    elif provider == "openrouter":
        config["provider"] = "openai"  # OpenRouter uses OpenAI-compatible API
        if api_key:
            config["config"]["api_key"] = api_key
            os.environ["OPENROUTER_API_KEY"] = api_key
        if base_url:
            config["config"]["openai_base_url"] = base_url
        else:
            config["config"]["openai_base_url"] = "https://openrouter.ai/api/v1"

    elif provider == "ollama":
        if base_url:
            config["config"]["ollama_base_url"] = base_url
        else:
            config["config"]["ollama_base_url"] = "http://localhost:11434"

    elif provider == "azure_openai":
        if api_key:
            config["config"]["api_key"] = api_key
        if base_url:
            config["config"]["azure_endpoint"] = base_url
        api_version = get_env("AZURE_API_VERSION", "2024-02-15-preview")
        config["config"]["api_version"] = api_version
        azure_deployment = get_env("AZURE_DEPLOYMENT")
        if azure_deployment:
            config["config"]["azure_deployment"] = azure_deployment

    elif provider == "deepseek":
        config["provider"] = "deepseek"
        if api_key:
            config["config"]["api_key"] = api_key
        if base_url:
            config["config"]["base_url"] = base_url

    elif provider == "together":
        config["provider"] = "together"
        if api_key:
            config["config"]["api_key"] = api_key
            os.environ["TOGETHER_API_KEY"] = api_key

    elif provider == "groq":
        config["provider"] = "groq"
        if api_key:
            config["config"]["api_key"] = api_key
            os.environ["GROQ_API_KEY"] = api_key

    else:
        # Generic OpenAI-compatible provider
        if api_key:
            config["config"]["api_key"] = api_key
        if base_url:
            config["config"]["openai_base_url"] = base_url

    logger.info(f"Configured LLM provider: {provider}, model: {model}")
    return config


def _build_embedder_config() -> Dict[str, Any]:
    """Build embedder configuration from environment variables."""
    provider = get_env("EMBEDDING_PROVIDER", get_env("LLM_PROVIDER", "openai"))
    model = get_env("EMBEDDING_MODEL", "text-embedding-3-small")
    dims = get_env_int("EMBEDDING_DIMS", 1536)
    api_key = get_env("EMBEDDING_API_KEY", get_env("LLM_API_KEY"))
    base_url = get_env("EMBEDDING_BASE_URL", get_env("LLM_BASE_URL"))

    config: Dict[str, Any] = {
        "provider": provider,
        "config": {
            "model": model,
            "embedding_dims": dims,
        },
    }

    # Provider-specific configurations
    if provider == "openai":
        if api_key:
            config["config"]["api_key"] = api_key
        if base_url:
            config["config"]["openai_base_url"] = base_url

    elif provider == "ollama":
        if base_url:
            config["config"]["ollama_base_url"] = base_url
        else:
            config["config"]["ollama_base_url"] = "http://localhost:11434"

    elif provider == "azure_openai":
        if api_key:
            config["config"]["api_key"] = api_key
        if base_url:
            config["config"]["azure_endpoint"] = base_url
        api_version = get_env("AZURE_API_VERSION", "2024-02-15-preview")
        config["config"]["api_version"] = api_version

    elif provider == "huggingface":
        config["provider"] = "huggingface"
        # HuggingFace uses local model, no API key needed

    else:
        # Generic configuration
        if api_key:
            config["config"]["api_key"] = api_key
        if base_url:
            config["config"]["base_url"] = base_url

    logger.info(f"Configured embedder provider: {provider}, model: {model}, dims: {dims}")
    return config


def _build_vector_store_config() -> Dict[str, Any]:
    """Build vector store configuration from environment variables."""
    provider = get_env("VECTOR_STORE_PROVIDER", "qdrant")

    if provider == "qdrant":
        config: Dict[str, Any] = {
            "provider": "qdrant",
            "config": {
                "collection_name": get_env("QDRANT_COLLECTION", "mem0_memories"),
            },
        }

        # Persist local Qdrant storage across restarts.
        # Note: mem0's Qdrant implementation will delete the local path on startup
        # when on_disk is False.
        config["config"]["on_disk"] = get_env_bool("QDRANT_ON_DISK", False)

        # Check if using local file storage or remote server
        qdrant_path = get_env("QDRANT_PATH")
        qdrant_host = get_env("QDRANT_HOST")

        if qdrant_path:
            # Local file storage (no Qdrant server needed)
            config["config"]["path"] = qdrant_path
            logger.info(f"Configured Qdrant with local storage: {qdrant_path}")
        elif qdrant_host:
            # Remote Qdrant server
            config["config"]["host"] = qdrant_host
            config["config"]["port"] = get_env_int("QDRANT_PORT", 6333)
            qdrant_api_key = get_env("QDRANT_API_KEY")
            if qdrant_api_key:
                config["config"]["api_key"] = qdrant_api_key
            logger.info(f"Configured Qdrant with remote server: {qdrant_host}")
        else:
            # Default to local file storage
            config["config"]["path"] = "./mem0_data"
            logger.info("Configured Qdrant with default local storage: ./mem0_data")

        # Set embedding dimensions
        dims = get_env_int("EMBEDDING_DIMS", 1536)
        config["config"]["embedding_model_dims"] = dims

    elif provider == "pgvector":
        database_url = get_env("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL is required for pgvector provider")

        config = {
            "provider": "pgvector",
            "config": {
                "connection_string": database_url,
                "collection_name": get_env("PGVECTOR_COLLECTION", "mem0_memories"),
                "embedding_model_dims": get_env_int("EMBEDDING_DIMS", 1536),
            },
        }
        logger.info("Configured pgvector vector store")

    elif provider == "chroma":
        config = {
            "provider": "chroma",
            "config": {
                "collection_name": get_env("CHROMA_COLLECTION", "mem0_memories"),
                "path": get_env("CHROMA_PATH", "./chroma_data"),
            },
        }
        logger.info("Configured Chroma vector store")

    else:
        raise ValueError(f"Unsupported vector store provider: {provider}")

    return config


def create_mem0_client() -> Memory:
    """Create and configure a Mem0 Memory client based on environment variables.

    Supports multiple LLM providers (OpenAI, Ollama, OpenRouter, Azure, DeepSeek, etc.)
    and vector store backends (Qdrant, pgvector, Chroma).

    Returns:
        Memory: Configured Mem0 Memory client
    """
    config: Dict[str, Any] = {}

    # Build LLM configuration
    config["llm"] = _build_llm_config()

    # Build embedder configuration
    config["embedder"] = _build_embedder_config()

    # Build vector store configuration
    config["vector_store"] = _build_vector_store_config()

    # Optional: Graph memory configuration
    if get_env_bool("ENABLE_GRAPH_MEMORY", False):
        config["graph_store"] = {
            "provider": "neo4j",
            "config": {
                "url": get_env("NEO4J_URL", "bolt://localhost:7687"),
                "username": get_env("NEO4J_USERNAME", "neo4j"),
                "password": get_env("NEO4J_PASSWORD", "password"),
            },
        }
        logger.info("Graph memory enabled with Neo4j")

    logger.info("Creating Mem0 Memory client with custom configuration")
    return Memory.from_config(config)


# Default user ID for memory operations
DEFAULT_USER_ID = get_env("DEFAULT_USER_ID", "default_user")
