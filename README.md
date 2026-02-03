# mcp-ai-memory

一个支持本地部署、自定义 LLM Provider 的 MCP (Model Context Protocol) 记忆服务器。基于 [Mem0](https://mem0.ai) 库实现，提供持久化的长期记忆存储能力。

## 特性

- **本地部署**: 无需依赖云服务，数据完全本地存储
- **多 LLM 支持**: OpenAI、Ollama、OpenRouter、Azure OpenAI、DeepSeek、Together、Groq 等
- **多向量库支持**: Qdrant（推荐）、pgvector、Chroma
- **丰富的工具集**: 添加、搜索、更新、删除记忆等完整 CRUD 操作
- **双传输模式**: 支持 SSE (HTTP) 和 stdio 两种传输协议
- **Docker 支持**: 提供完整的容器化部署方案

## 提供的工具

| 工具 | 描述 |
| --- | --- |
| `add_memory` | 保存文本或对话历史到长期记忆 |
| `search_memories` | 语义搜索现有记忆 |
| `get_memories` | 列出所有记忆（支持过滤） |
| `get_memory` | 通过 memory_id 获取单条记忆 |
| `update_memory` | 更新指定记忆的内容 |
| `delete_memory` | 删除单条记忆 |
| `delete_all_memories` | 批量删除指定范围的记忆 |
| `get_memory_history` | 获取记忆的变更历史 |
| `reset_memories` | 重置所有记忆（慎用） |

## 快速开始

### 方式一：使用 uv（推荐）

1. **安装 uv**:

   ```bash
   pip install uv
   ```

2. **克隆并安装**:

   ```bash
   git clone https://github.com/MorseWayne/mcp-ai-memory.git
   cd mcp-ai-memory
   uv venv
   uv pip install -e .
   ```

3. **配置环境变量**:

   ```bash
   cp .env.example .env
   # 编辑 .env 文件，配置你的 LLM 和向量库
   ```

4. **运行服务**:

   ```bash
   # SSE 模式
   TRANSPORT=sse uv run python -m mem0_local_mcp.server

   # 或 stdio 模式
   TRANSPORT=stdio uv run python -m mem0_local_mcp.server
   ```

### 方式二：使用 Docker

1. **构建镜像**:

   ```bash
   docker build -t mcp-ai-memory .
   ```

2. **创建配置文件**:

   ```bash
   cp .env.example .env
   # 编辑 .env 文件
   ```

3. **运行容器**:

   ```bash
   # SSE 模式
   docker run --rm -d \
     --name mcp-ai-memory \
     --env-file .env \
     -v ./mem0_data:/app/mem0_data \
     -p 8050:8050 \
     mcp-ai-memory

   # stdio 模式
   docker run --rm -i \
     --env-file .env \
     -e TRANSPORT=stdio \
     -v ./mem0_data:/app/mem0_data \
     mcp-ai-memory
   ```

### 方式三：使用 pip

```bash
pip install -e .
mcp-ai-memory
```

## 配置说明

### LLM 配置

支持多种 LLM Provider，在 `.env` 中配置：

#### OpenAI

```env
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-xxx
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMS=1536
```

#### Ollama（本地）

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

### 向量库配置

#### Qdrant 本地存储（默认，无需额外服务）

```env
VECTOR_STORE_PROVIDER=qdrant
QDRANT_PATH=./mem0_data
QDRANT_COLLECTION=mem0_memories
```

#### Qdrant 服务器

```env
VECTOR_STORE_PROVIDER=qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=mem0_memories
```

#### PostgreSQL + pgvector

```env
VECTOR_STORE_PROVIDER=pgvector
DATABASE_URL=postgresql://user:password@localhost:5432/mem0
```

## MCP 客户端配置

### SSE 模式（推荐用于持久服务）

先启动服务器，然后在 MCP 客户端中配置：

```json
{
  "mcpServers": {
    "mem0-local": {
      "transport": "sse",
      "url": "http://localhost:8050/sse"
    }
  }
}
```

### stdio 模式（适用于 Claude Desktop 等）

#### Python 直接运行

```json
{
  "mcpServers": {
    "mem0-local": {
      "command": "python",
      "args": ["-m", "mem0_local_mcp.server"],
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

#### Docker 运行

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

## 使用示例

### 添加记忆

```
"请记住我喜欢吃辣的食物，不吃海鲜"
→ 调用 add_memory(text="用户喜欢辣食，不吃海鲜")
```

### 搜索记忆

```
"我之前说过什么饮食偏好？"
→ 调用 search_memories(query="饮食偏好 食物喜好")
```

### 更新记忆

```
"更新一下，我现在也开始吃海鲜了"
→ 调用 update_memory(memory_id="xxx", text="用户喜欢辣食，现在也吃海鲜")
```

### 删除记忆

```
"删除关于我饮食偏好的记录"
→ 先 search_memories 找到相关记忆
→ 再 delete_memory(memory_id="xxx")
```

## 环境变量参考

| 变量 | 描述 | 默认值 |
| --- | --- | --- |
| `TRANSPORT` | 传输协议 (sse/stdio) | `sse` |
| `HOST` | SSE 绑定地址 | `0.0.0.0` |
| `PORT` | SSE 端口 | `8050` |
| `LLM_PROVIDER` | LLM 提供商 | `openai` |
| `LLM_BASE_URL` | LLM API 地址 | - |
| `LLM_API_KEY` | LLM API 密钥 | - |
| `LLM_MODEL` | LLM 模型名称 | `gpt-4o-mini` |
| `EMBEDDING_PROVIDER` | Embedding 提供商 | 同 LLM_PROVIDER |
| `EMBEDDING_MODEL` | Embedding 模型 | `text-embedding-3-small` |
| `EMBEDDING_DIMS` | Embedding 维度 | `1536` |
| `VECTOR_STORE_PROVIDER` | 向量库类型 | `qdrant` |
| `QDRANT_PATH` | Qdrant 本地路径 | `./mem0_data` |
| `DEFAULT_USER_ID` | 默认用户 ID | `default_user` |
| `LOG_LEVEL` | 日志级别 | `INFO` |

## 完全本地部署示例

使用 Ollama + Qdrant 本地存储，无需任何外部 API：

1. **安装并启动 Ollama**:

   ```bash
   # 拉取模型
   ollama pull qwen2.5:7b
   ollama pull nomic-embed-text
   ```

2. **配置 .env**:

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

3. **启动服务**:

   ```bash
   python -m mem0_local_mcp.server
   ```

## License

Apache 2.0
