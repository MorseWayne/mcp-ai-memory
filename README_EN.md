# mcp-ai-memory

An MCP (Model Context Protocol) memory server supporting local deployment and custom LLM Providers. Based on the [Mem0](https://mem0.ai) library, it provides persistent long-term memory storage capabilities.

[中文文档](README.md) | [English Documentation](README_EN.md)

## Features

- **Local Deployment**: No dependency on cloud services, data is stored completely locally
- **Multi-LLM Support**: OpenAI, Ollama, OpenRouter, Azure OpenAI, DeepSeek, Together, Groq, etc.
- **Multi-Vector Store Support**: Qdrant (Recommended), pgvector, Chroma
- **Rich Toolset**: Complete CRUD operations including adding, searching, updating, and deleting memories
- **Multiple Transport Modes**: Supports Streamable HTTP (recommended), SSE, and stdio protocols
- **Docker Support**: Provides complete containerized deployment solutions
- **Cursor Agent Skill**: Built-in intelligent Skill to automatically sync project knowledge to long-term memory

## Tools Provided

| Tool | Description |
| --- | --- |
| `add_memory` | Save text or conversation history to long-term memory |
| `search_memories` | Semantic search of existing memories |
| `get_memories` | List all memories (supports filtering) |
| `get_memory` | Get a single memory by memory_id |
| `update_memory` | Update content of a specific memory |
| `delete_memory` | Delete a single memory |
| `delete_all_memories` | Batch delete memories within a specified range |
| `get_memory_history` | Get change history of a memory |
| `reset_memories` | Reset all memories (use with caution) |

## Quick Start

### Option 1: Using uv (Recommended)

1. **Install uv**:

   ```bash
   pip install uv
   ```

2. **Clone and Install**:

   ```bash
   git clone https://github.com/MorseWayne/mcp-ai-memory.git
   cd mcp-ai-memory
   uv venv
   uv pip install -e .
   ```

3. **Configure Environment Variables**:

   ```bash
   cp .env.example .env
   # Edit .env file to configure your LLM and vector store
   ```

4. **Run Server**:

   ```bash
   # Streamable HTTP Mode (recommended, auto-recovers after server restart)
   TRANSPORT=streamable-http uv run python -m mcp_ai_memory.server

   # Or SSE Mode (deprecated)
   TRANSPORT=sse uv run python -m mcp_ai_memory.server

   # Or stdio Mode
   TRANSPORT=stdio uv run python -m mcp_ai_memory.server
   ```

### Option 2: Using Docker Compose (Recommended for Production)

```bash
# Start only Qdrant service
docker compose up -d qdrant

# Or start full service (including MCP service and Qdrant)
docker compose up -d
```

Detailed deployment guide see [DEPLOYMENT.md](DEPLOYMENT.md).

## Configuration

### LLM Configuration

Supports multiple LLM Providers, configure in `.env`:

#### OpenAI

```env
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-xxx
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMS=1536
```

#### Ollama (Local)

```env
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=qwen2.5:7b
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIMS=768
```

#### OpenRouter

```env
LLM_PROVIDER=openrouter
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=sk-or-xxx
LLM_MODEL=anthropic/claude-3.5-sonnet
```

#### DeepSeek

```env
LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=sk-xxx
LLM_MODEL=deepseek-chat
```

### Vector Store Configuration

#### Qdrant Local Storage (Suitable for Single Process Deployment)

```env
VECTOR_STORE_PROVIDER=qdrant
QDRANT_PATH=./mem0_data
QDRANT_COLLECTION=mem0_memories
```

> ⚠️ Note: Local storage mode will have file lock conflicts when accessed by multiple processes simultaneously. If concurrent access is needed (e.g., running tests and server simultaneously), it is recommended to use Qdrant Server mode.

#### Qdrant Server (Recommended, Supports Concurrent Access)

```env
VECTOR_STORE_PROVIDER=qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=mem0_memories
```

**Quick Start Qdrant Service using Docker**:

```bash
# Method 1: Using docker compose (Recommended)
docker compose up -d qdrant

# Method 2: Using docker run directly
docker run -d \
  --name qdrant-vectordb \
  -p 6333:6333 \
  -p 6334:6334 \
  -v qdrant-storage:/qdrant/storage \
  qdrant/qdrant:latest
```

Access Qdrant Dashboard: <http://localhost:6333/dashboard>

#### PostgreSQL + pgvector

```env
VECTOR_STORE_PROVIDER=pgvector
DATABASE_URL=postgresql://user:password@localhost:5432/mem0
```

#### Chroma

```env
VECTOR_STORE_PROVIDER=chroma
CHROMA_PATH=./chroma_data
```

## Quick Start using Docker Compose

The project provides `docker-compose.yml` for one-click service startup:

```bash
# Start all services (including MCP service and Qdrant)
docker compose up -d

# Start only Qdrant service
docker compose up -d qdrant

# Check service status
docker compose ps

# Stop services
docker compose down

# Clean all data (including data volumes)
docker compose down -v
```

**Configuration File** (`.env`) using Qdrant Server:

```env
VECTOR_STORE_PROVIDER=qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=mem0_memories
```

## MCP Client Configuration

### Configuration File Location

MCP configuration file locations for different clients:

| Client | Configuration File Path |
| --- | --- |
| Cursor | `~/.cursor/mcp.json` (Global) or `{project}/.cursor/mcp.json` (Project level) |
| Claude Desktop (macOS) | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Claude Desktop (Windows) | `%APPDATA%\Claude\claude_desktop_config.json` |

### Streamable HTTP Mode (Recommended for Persistent Service)

Streamable HTTP is the recommended transport mode in MCP spec:
- **Stateless connections**: Auto-recovers after server restart, no "uninitialized" errors
- **Better compatibility**: Works with various network environments and proxies

First start the server:

```bash
TRANSPORT=streamable-http uv run python -m mcp_ai_memory.server
```

Then add to MCP client configuration file:

```json
{
  "mcpServers": {
    "mem0-local": {
      "transport": "http",
      "url": "http://localhost:8050/mcp"
    }
  }
}
```

### stdio Mode (Suitable for Claude Desktop, Cursor, etc.)

stdio mode does not require pre-starting the service, the client will automatically launch the process.

#### Using uv (Recommended)

```json
{
  "mcpServers": {
    "mem0-local": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/mcp-ai-memory", "python", "-m", "mcp_ai_memory.server"],
      "env": {
        "TRANSPORT": "stdio",
        "LLM_PROVIDER": "ollama",
        "LLM_BASE_URL": "http://localhost:11434",
        "LLM_MODEL": "qwen2.5:7b",
        "EMBEDDING_PROVIDER": "ollama",
        "EMBEDDING_MODEL": "nomic-embed-text",
        "EMBEDDING_DIMS": "768",
        "VECTOR_STORE_PROVIDER": "qdrant",
        "QDRANT_PATH": "/path/to/mem0_data"
      }
    }
  }
}
```

#### Using Python Directly

```json
{
  "mcpServers": {
    "mem0-local": {
      "command": "python",
      "args": ["-m", "mcp_ai_memory.server"],
      "env": {
        "TRANSPORT": "stdio",
        "LLM_PROVIDER": "ollama",
        "LLM_BASE_URL": "http://localhost:11434",
        "LLM_MODEL": "qwen2.5:7b",
        "EMBEDDING_PROVIDER": "ollama",
        "EMBEDDING_MODEL": "nomic-embed-text",
        "EMBEDDING_DIMS": "768",
        "VECTOR_STORE_PROVIDER": "qdrant",
        "QDRANT_PATH": "/path/to/mem0_data"
      }
    }
  }
}
```

#### Using Docker

```json
{
  "mcpServers": {
    "mem0-local": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-e", "TRANSPORT=stdio",
        "-e", "LLM_PROVIDER",
        "-e", "LLM_BASE_URL",
        "-e", "LLM_API_KEY",
        "-e", "LLM_MODEL",
        "-e", "EMBEDDING_MODEL",
        "-e", "EMBEDDING_DIMS",
        "-v", "./mem0_data:/app/mem0_data",
        "mcp-ai-memory"
      ],
      "env": {
        "LLM_PROVIDER": "openai",
        "LLM_BASE_URL": "https://api.openai.com/v1",
        "LLM_API_KEY": "sk-xxx",
        "LLM_MODEL": "gpt-4o-mini",
        "EMBEDDING_MODEL": "text-embedding-3-small",
        "EMBEDDING_DIMS": "1536"
      }
    }
  }
}
```

## Usage Examples

### Add Memory

```
"Please remember that I like spicy food and don't eat seafood"
→ Call add_memory(text="User likes spicy food, does not eat seafood")
```

### Search Memories

```
"What food preferences did I mention before?"
→ Call search_memories(query="food preferences")
```

### Update Memory

```
"Update: I started eating seafood now"
→ Call update_memory(memory_id="xxx", text="User likes spicy food, now also eats seafood")
```

### Delete Memory

```
"Delete records about my food preferences"
→ First search_memories to find relevant memory
→ Then delete_memory(memory_id="xxx")
```

## Cursor Agent Skill (Recommended)

This project provides a Cursor Agent Skill that allows AI assistants to automatically manage long-term memory of project knowledge.

### Features

- **Auto Trigger**: Automatically activated when user asks about project info (e.g., "Help me understand this project", "Introduce project functions")
- **Sync Changes**: Automatically syncs changes to memory system when code, interface, or docs are modified
- **Smart Decision**: Automatically chooses add, update, or delete memory operations

### Installation

#### Method 1: Project-level Installation (Recommended)

If you cloned this project, the Skill is already included in `.cursor/skills/project-memory-sync/` directory, Cursor will automatically recognize it.

#### Method 2: Global Installation

Copy the Skill to personal directory to use in all projects:

```bash
mkdir -p ~/.cursor/skills/project-memory-sync
cp .cursor/skills/project-memory-sync/SKILL.md ~/.cursor/skills/project-memory-sync/
```

### Usage Scenarios

#### Scenario A: Understanding Project

```
User: "Help me familiarize with this project"
User: "What are the core functions of this project?"
User: "Introduce the project architecture"

→ Agent will first search existing memories, combine with code analysis to answer
→ If new important info is found, it automatically saves to memory
```

#### Scenario B: After Code Changes

```
User: (Modified an API interface)
User: (Added a new feature module)
User: (Deleted a feature)

→ Agent automatically analyzes changes
→ Selects add_memory / update_memory / delete_memory to sync memory
```

### Memory Format Example

Skill saves memory in standardized format:

```
"mcp-ai-memory project uses Mem0 library for long-term memory storage, supports Qdrant and pgvector vector stores"
"mcp-ai-memory's add_memory interface supports text, messages, user_id, metadata parameters"
"Project supports Streamable HTTP, SSE and stdio transport modes, streamable-http is recommended"
```

## Memory Extraction Prompt Configuration

This project uses custom prompts to control how LLM extracts memories from input. By default, it uses an enhanced prompt that supports storing both personal preferences and project knowledge/technical documentation.

### Built-in Prompt Types

| Type | Description | Use Case |
| --- | --- | --- |
| `default` | Enhanced: Supports personal preferences + project knowledge/technical docs | Need to store project knowledge, API design, code conventions, etc. |
| `personal` | Original: Only supports personal preferences (original mem0 behavior) | Only need to store user personal preferences and info |

### Configuration Methods

#### Using Built-in Types

```env
# Use enhanced type (default)
FACT_EXTRACTION_PROMPT_TYPE=default

# Use original type
FACT_EXTRACTION_PROMPT_TYPE=personal
```

#### Load Custom Prompt from File

```env
CUSTOM_FACT_EXTRACTION_PROMPT_FILE=/path/to/custom_prompt.txt
```

You can use `{current_date}` placeholder in the prompt file, which will be automatically replaced with current date.

#### Set Custom Prompt Directly

```env
CUSTOM_FACT_EXTRACTION_PROMPT="Your custom prompt here..."
```

### Configuration Priority

1. `CUSTOM_FACT_EXTRACTION_PROMPT` (set directly via environment variable)
2. `CUSTOM_FACT_EXTRACTION_PROMPT_FILE` (load from file)
3. `FACT_EXTRACTION_PROMPT_TYPE` (use built-in type)

### Custom Prompt Writing Guide

A custom prompt should:

1. Define the types of information to extract
2. Provide few-shot examples
3. Specify output format as JSON: `{"facts": ["fact1", "fact2", ...]}`
4. Describe language detection rules (recommend keeping input language)

Refer to the default prompt templates in `src/mcp_ai_memory/prompts.py`.

## Environment Variables Reference

| Variable | Description | Default |
| --- | --- | --- |
| `TRANSPORT` | Transport protocol (streamable-http/sse/stdio) | `sse` |
| `HOST` | HTTP Bind Address | `0.0.0.0` |
| `PORT` | HTTP Port | `8050` |
| `LLM_PROVIDER` | LLM Provider | `openai` |
| `LLM_BASE_URL` | LLM API URL | - |
| `LLM_API_KEY` | LLM API Key | - |
| `LLM_MODEL` | LLM Model Name | `gpt-4o-mini` |
| `EMBEDDING_PROVIDER` | Embedding Provider | Same as LLM_PROVIDER |
| `EMBEDDING_MODEL` | Embedding Model | `text-embedding-3-small` |
| `EMBEDDING_DIMS` | Embedding Dimensions | `1536` |
| `VECTOR_STORE_PROVIDER` | Vector Store Type | `qdrant` |
| `QDRANT_PATH` | Qdrant Local Path | `./mem0_data` |
| `DEFAULT_USER_ID` | Default User ID | `default_user` |
| `LOG_LEVEL` | Log Level | `INFO` |
| `FACT_EXTRACTION_PROMPT_TYPE` | Prompt type (default/personal) | `default` |
| `CUSTOM_FACT_EXTRACTION_PROMPT_FILE` | Custom prompt file path | - |
| `CUSTOM_FACT_EXTRACTION_PROMPT` | Set custom prompt directly | - |

## Fully Local Deployment Examples

### Plan A: Completely Offline (Recommended for Dev Env)

Use Ollama + Qdrant Local Storage, no external APIs required:

1. **Install and Start Ollama**:

   ```bash
   # Pull models
   ollama pull qwen2.5:7b
   ollama pull nomic-embed-text
   ```

2. **Configure .env**:

   ```env
   TRANSPORT=sse
   HOST=0.0.0.0
   PORT=8050
   
   LLM_PROVIDER=ollama
   LLM_BASE_URL=http://localhost:11434
   LLM_MODEL=qwen2.5:7b
   
   EMBEDDING_PROVIDER=ollama
   EMBEDDING_MODEL=nomic-embed-text
   EMBEDDING_DIMS=768
   
   VECTOR_STORE_PROVIDER=qdrant
   QDRANT_PATH=./mem0_data
   ```

3. **Start Service**:

   ```bash
   python -m mcp_ai_memory.server
   ```

### Plan B: Using Qdrant Service (Recommended for Production)

Supports concurrent access and better scalability:

1. **Start Qdrant Service**:

   ```bash
   docker compose up -d qdrant
   ```

2. **Configure .env**:

   ```env
   TRANSPORT=sse
   HOST=0.0.0.0
   PORT=8050
   
   LLM_PROVIDER=openai
   LLM_BASE_URL=https://api.vectorengine.ai/v1
   LLM_API_KEY=sk-xxx
   LLM_MODEL=gpt-4o-mini
   
   EMBEDDING_PROVIDER=openai
   EMBEDDING_MODEL=text-embedding-3-small
   EMBEDDING_DIMS=1536
   
   VECTOR_STORE_PROVIDER=qdrant
   QDRANT_HOST=localhost
   QDRANT_PORT=6333
   QDRANT_COLLECTION=mem0_memories
   ```

3. **Start MCP Service**:

   ```bash
   TRANSPORT=sse uv run python -m mcp_ai_memory.server
   ```

### Plan C: Full Docker Compose Deployment

Create a complete multi-container environment (including MCP service and Qdrant):

```bash
# Start all services
docker compose up -d
```

## Troubleshooting

### Issue 1: Qdrant File Lock Error

If you see error: `Storage folder is already accessed by another instance of Qdrant client`

**Solution**:

- Switch to Qdrant Server mode (refer to "Plan B")
- Or close all other processes accessing the same data file

```bash
# Stop all related processes
pkill -f mcp_ai_memory
pkill -f mem0

# Clean local Qdrant files
rm -rf ./mem0_data

# Restart
docker compose up -d qdrant
TRANSPORT=sse uv run python -m mcp_ai_memory.server
```

### Issue 2: API Connection Failure

Error message: `Connection error` or `API connection failed`

**Troubleshooting Steps**:

1. Run diagnostic script:

   ```bash
   uv run python tests/diagnose_api.py
   ```

2. Check `.env` configuration:
   - Is `LLM_BASE_URL` correct?
   - Is `LLM_API_KEY` valid?
   - Is network connection normal?

3. Test API connection:

   ```bash
   curl -X POST https://api.vectorengine.ai/v1/chat/completions \
     -H "Authorization: Bearer sk-xxx" \
     -H "Content-Type: application/json" \
     -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"test"}],"max_tokens":10}'
   ```

### Issue 3: Test Script Cannot Connect to MCP Service

Ensure MCP service is running:

```bash
# Check service status
ps aux | grep mcp_ai_memory

# View service logs
tail -f /tmp/mcp_server.log

# Test connection
curl http://localhost:8050/sse
```

### Issue 4: Memory Added Successfully But Cannot Be Searched

If `add_memory` returns success, but `search_memories` or `get_memories` returns empty results:

**Possible Cause**: LLM did not extract valid memory facts from the input.

**Troubleshooting Steps**:

1. **Enable Debug Logging**:

   ```env
   LOG_LEVEL=DEBUG
   ```

2. **Check Log Output**, look for:

   ```
   [DEBUG] No memories extracted by LLM! Input: '...'
   ```

   or

   ```
   Memory operation completed for user=xxx, added=0 memories
   ```

3. **Common Causes and Solutions**:

   | Log Message | Cause | Solution |
   | --- | --- | --- |
   | `added=0 memories` | LLM determined input contains no storable info | Check input format (see below) |
   | `event=NONE` | LLM determined as duplicate or not worth storing | Input may already exist or is not a factual statement |

4. **Input Format Suggestions**:

   ✅ **Good Input** (clear factual statements):
   ```
   "I like programming in Python, especially using FastAPI framework"
   "mcp-ai-memory is an MCP memory server based on Mem0"
   "The project uses Qdrant as the vector database"
   ```

   ❌ **Bad Input** (questions or vague descriptions):
   ```
   "mcp-ai-memory project features design architecture what"  # Like search keywords, not statements
   "How is this project?"  # Question, no factual info
   ```

5. **If It's a Project Knowledge Storage Issue**:

   Ensure you're using the enhanced prompt (default):

   ```env
   FACT_EXTRACTION_PROMPT_TYPE=default
   ```

   The original mem0 prompt only supports personal preferences, not project knowledge/technical docs.

## License

Apache 2.0
