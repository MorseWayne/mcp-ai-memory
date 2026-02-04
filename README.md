# mcp-ai-memory

一个支持本地部署、自定义 LLM Provider 的 MCP (Model Context Protocol) 记忆服务器。基于 [Mem0](https://mem0.ai) 库实现，提供持久化的长期记忆存储能力。

## 特性

- **本地部署**: 无需依赖云服务，数据完全本地存储
- **多 LLM 支持**: OpenAI、Ollama、OpenRouter、Azure OpenAI、DeepSeek、Together、Groq 等
- **多向量库支持**: Qdrant（推荐）、pgvector、Chroma
- **丰富的工具集**: 添加、搜索、更新、删除记忆等完整 CRUD 操作
- **双传输模式**: 支持 SSE (HTTP) 和 stdio 两种传输协议
- **Docker 支持**: 提供完整的容器化部署方案
- **Cursor Agent Skill**: 内置智能 Skill，自动同步项目知识到长期记忆

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
   TRANSPORT=sse uv run python -m mcp_ai_memory.server

   # 或 stdio 模式
   TRANSPORT=stdio uv run python -m mcp_ai_memory.server
   ```

### 方式二：使用 Docker Compose（推荐生产）

```bash
# 仅启动 Qdrant 服务
docker compose up -d qdrant

# 或启动完整服务（包括 MCP 服务和 Qdrant）
docker compose up -d
```

详细部署指南见 [DEPLOYMENT.md](DEPLOYMENT.md)。

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

#### Qdrant 本地存储（适合单进程部署）

```env
VECTOR_STORE_PROVIDER=qdrant
QDRANT_PATH=./mem0_data
QDRANT_COLLECTION=mem0_memories
```

> ⚠️ 注意：本地存储模式在多进程同时访问时会出现文件锁冲突。如果需要并发访问（如同时运行测试和服务），建议使用 Qdrant 服务器模式。

#### Qdrant 服务器（推荐，支持并发访问）

```env
VECTOR_STORE_PROVIDER=qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=mem0_memories
```

**使用 Docker 快速启动 Qdrant 服务**：

```bash
# 方式 1：使用 docker compose（推荐）
docker compose up -d qdrant

# 方式 2：直接使用 docker run
docker run -d \
  --name qdrant-vectordb \
  -p 6333:6333 \
  -p 6334:6334 \
  -v qdrant-storage:/qdrant/storage \
  qdrant/qdrant:latest
```

访问 Qdrant 管理界面：<http://localhost:6333/dashboard>

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

## 使用 Docker Compose 快速启动

项目提供了 `docker-compose.yml`，可以一键启动服务：

```bash
# 启动所有服务（包括 MCP 服务和 Qdrant）
docker compose up -d

# 仅启动 Qdrant 服务
docker compose up -d qdrant

# 查看服务状态
docker compose ps

# 停止服务
docker compose down

# 清理所有数据（包括数据卷）
docker compose down -v
```

**配置文件**（`.env`）中使用 Qdrant 服务器：

```env
VECTOR_STORE_PROVIDER=qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=mem0_memories
```

## MCP 客户端配置

### 配置文件位置

不同客户端的 MCP 配置文件位置：

| 客户端 | 配置文件路径 |
| --- | --- |
| Cursor | `~/.cursor/mcp.json`（全局）或 `{项目}/.cursor/mcp.json`（项目级） |
| Claude Desktop (macOS) | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Claude Desktop (Windows) | `%APPDATA%\Claude\claude_desktop_config.json` |

### SSE 模式（推荐用于持久服务）

先启动服务器：

```bash
TRANSPORT=sse uv run python -m mcp_ai_memory.server
```

然后在 MCP 客户端配置文件中添加：

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

### stdio 模式（适用于 Claude Desktop、Cursor 等）

stdio 模式无需预先启动服务，客户端会自动拉起进程。

#### 使用 uv 运行（推荐）

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

#### Python 直接运行

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

## Cursor Agent Skill（推荐）

本项目提供了一个 Cursor Agent Skill，可以让 AI 助手自动管理项目知识的长期记忆。

### 功能特点

- **自动触发**：当用户询问项目信息（如"帮我熟悉这个项目"、"介绍一下这个项目的功能"）时自动激活
- **变更同步**：当修改代码、接口、文档后，自动将变更同步到记忆系统
- **智能判断**：自动选择添加、更新或删除记忆的操作

### 安装方式

#### 方式一：项目级安装（推荐）

如果你克隆了本项目，Skill 已经包含在 `.cursor/skills/project-memory-sync/` 目录中，Cursor 会自动识别。

#### 方式二：全局安装

将 Skill 复制到个人目录，所有项目都可使用：

```bash
mkdir -p ~/.cursor/skills/project-memory-sync
cp .cursor/skills/project-memory-sync/SKILL.md ~/.cursor/skills/project-memory-sync/
```

### 使用场景

#### 场景 A：了解项目

```
用户: "帮我熟悉一下这个项目"
用户: "这个项目的核心功能是什么？"
用户: "介绍一下项目的设计架构"

→ Agent 会先搜索已有记忆，结合代码分析回答
→ 如果发现新的重要信息，会自动保存到记忆
```

#### 场景 B：代码变更后

```
用户: (修改了 API 接口)
用户: (新增了一个功能模块)
用户: (删除了某个功能)

→ Agent 会自动分析变更内容
→ 选择 add_memory / update_memory / delete_memory 同步记忆
```

### 记忆格式示例

Skill 会以标准化格式保存记忆：

```
"mcp-ai-memory 项目使用 Mem0 库实现长期记忆存储，支持 Qdrant 和 pgvector 向量库"
"mcp-ai-memory 的 add_memory 接口支持 text、messages、user_id、metadata 等参数"
"项目支持 SSE 和 stdio 两种传输模式，通过 TRANSPORT 环境变量切换"
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

### 方案 A：完全离线（推荐开发环境）

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
   python -m mcp_ai_memory.server
   ```

### 方案 B：使用 Qdrant 服务（推荐生产环境）

支持并发访问和更好的扩展性：

1. **启动 Qdrant 服务**:

   ```bash
   docker compose up -d qdrant
   ```

2. **配置 .env**:

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

3. **启动 MCP 服务**:

   ```bash
   TRANSPORT=sse uv run python -m mcp_ai_memory.server
   ```

### 方案 C：完整 Docker Compose 部署

创建完整的多容器环境（包括 MCP 服务和 Qdrant）：

```bash
# 启动所有服务
docker compose up -d
```

## 故障排查

### 问题 1：Qdrant 文件锁错误

如果看到错误：`Storage folder is already accessed by another instance of Qdrant client`

**解决方案**：

- 切换到 Qdrant 服务器模式（参考"方案 B"）
- 或者关闭所有其他访问同一数据文件的进程

```bash
# 停止所有相关进程
pkill -f mcp_ai_memory
pkill -f mem0

# 清理本地 Qdrant 文件
rm -rf ./mem0_data

# 重新启动
docker compose up -d qdrant
TRANSPORT=sse uv run python -m mcp_ai_memory.server
```

### 问题 2：API 连接失败

错误消息：`Connection error` 或 `API 连接失败`

**排查步骤**：

1. 运行诊断脚本：

   ```bash
   uv run python tests/diagnose_api.py
   ```

2. 检查 `.env` 配置：
   - `LLM_BASE_URL` 是否正确
   - `LLM_API_KEY` 是否有效
   - 网络连接是否正常

3. 测试 API 连接：

   ```bash
   curl -X POST https://api.vectorengine.ai/v1/chat/completions \
     -H "Authorization: Bearer sk-xxx" \
     -H "Content-Type: application/json" \
     -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"test"}],"max_tokens":10}'
   ```

### 问题 3：测试脚本无法连接到 MCP 服务

确保 MCP 服务正在运行：

```bash
# 检查服务状态
ps aux | grep mcp_ai_memory

# 查看服务日志
tail -f /tmp/mcp_server.log

# 测试连接
curl http://localhost:8050/sse
```

## License

Apache 2.0
