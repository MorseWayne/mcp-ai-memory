# Deployment Guide - MCP AI Memory

本指南详细说明如何部署 MCP AI Memory 服务。

## 前置要求

- Docker 和 Docker Compose（推荐）
- 或 Python 3.10+、uv 包管理器
- 有效的 LLM API 密钥（或本地 Ollama）

## 部署方案选择

| 方案 | 场景 | 复杂度 | 扩展性 |
|------|------|--------|-------|
| **单进程本地存储** | 开发测试 | ⭐ | 低 |
| **Qdrant 服务 + 本地** | 小规模应用 | ⭐⭐ | 中 |
| **Docker Compose** | 生产环境 | ⭐⭐⭐ | 高 |
| **Kubernetes** | 大规模部署 | ⭐⭐⭐⭐ | 很高 |

## 方案 1：本地开发（推荐）

### 适用场景
- 个人开发测试
- 不需要并发访问
- 一台机器上运行

### 步骤

1. **安装依赖**
   ```bash
   git clone https://github.com/MorseWayne/mcp-ai-memory.git
   cd mcp-ai-memory
   uv sync
   ```

2. **配置 .env**
   ```bash
   cp .env.example .env
   # 编辑 .env，配置 LLM 和 Embedding API
   ```

3. **运行服务**
   ```bash
   TRANSPORT=sse uv run python -m mcp_ai_memory.server
   ```

### 优点
- 快速启动
- 无需 Docker
- 适合学习

### 缺点
- 单进程限制
- 文件锁冲突（多进程）
- 难以扩展

---

## 方案 2：Qdrant 服务 + 本地运行（推荐测试环境）

### 适用场景
- 需要运行测试脚本
- 同时需要 MCP 服务
- 单机部署

### 步骤

1. **启动 Qdrant 服务**
   ```bash
   docker-compose up -d qdrant
   ```

2. **验证服务**
   ```bash
   curl http://localhost:6333/health
   # 应返回：{"status":"ok"}
   ```

3. **配置 .env**
   ```env
   VECTOR_STORE_PROVIDER=qdrant
   QDRANT_HOST=localhost
   QDRANT_PORT=6333
   ```

4. **启动 MCP 服务**
   ```bash
   TRANSPORT=sse uv run python -m mcp_ai_memory.server
   ```

5. **在新终端运行测试**
   ```bash
   uv run python test_mcp_server.py
   ```

### 优点
- 支持并发访问
- 测试环境可靠
- 简单快速

### 缺点
- 需要 Docker
- 单机限制
- 不适合生产高负载

---

## 方案 3：完整 Docker Compose（推荐生产环境）

### 适用场景
- 生产环境部署
- 完整容器化
- 易于管理和扩展

### 步骤

1. **创建 .env 文件**
   ```bash
   cp .env.example .env
   ```

2. **编辑 .env 配置**
   ```env
   LLM_PROVIDER=openai
   LLM_BASE_URL=https://api.openai.com/v1
   LLM_API_KEY=sk-xxx
   LLM_MODEL=gpt-4o-mini
   
   EMBEDDING_MODEL=text-embedding-3-small
   EMBEDDING_DIMS=1536
   
   QDRANT_COLLECTION=mem0_memories
   ```

3. **启动所有服务**
   ```bash
   docker-compose -f docker-compose.full.yml up -d
   ```

4. **验证服务**
   ```bash
   # 检查容器状态
   docker-compose -f docker-compose.full.yml ps
   
   # 查看 MCP 服务日志
   docker-compose -f docker-compose.full.yml logs -f mcp-ai-memory
   ```

5. **测试服务**
   ```bash
   curl http://localhost:8050/
   ```

### 优点
- 完全容器化
- 易于版本管理
- 易于备份和恢复
- 生产级别

### 缺点
- 需要 Docker Compose
- 资源占用较多
- 初始化较慢

### 常用命令

```bash
# 启动服务
docker-compose -f docker-compose.full.yml up -d

# 查看日志
docker-compose -f docker-compose.full.yml logs -f

# 停止服务
docker-compose -f docker-compose.full.yml down

# 清理数据（包括数据卷）
docker-compose -f docker-compose.full.yml down -v

# 重启特定服务
docker-compose -f docker-compose.full.yml restart mcp-ai-memory

# 重建镜像
docker-compose -f docker-compose.full.yml build --no-cache
```

---

## 方案 4：Kubernetes 部署（企业级）

### 适用场景
- 企业级应用
- 需要高可用性
- 大规模部署

### 基础配置

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-ai-memory
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mcp-ai-memory
  template:
    metadata:
      labels:
        app: mcp-ai-memory
    spec:
      containers:
      - name: mcp-ai-memory
        image: mcp-ai-memory:latest
        ports:
        - containerPort: 8050
        env:
        - name: LLM_PROVIDER
          valueFrom:
            configMapKeyRef:
              name: mcp-config
              key: llm-provider
        - name: QDRANT_HOST
          value: qdrant-service
        - name: QDRANT_PORT
          value: "6333"
        healthCheck:
          httpGet:
            path: /
            port: 8050
          initialDelaySeconds: 30
          periodSeconds: 10

---
apiVersion: v1
kind: Service
metadata:
  name: mcp-ai-memory-service
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8050
  selector:
    app: mcp-ai-memory
```

---

## 监控和维护

### 监控关键指标

1. **Qdrant 性能**
   ```bash
   # 查看集合统计
   curl http://localhost:6333/collections
   ```

2. **MCP 服务健康**
   ```bash
   # 健康检查
   curl http://localhost:8050/health
   ```

3. **日志分析**
   ```bash
   # 查看实时日志
   docker logs -f qdrant-vectordb
   docker logs -f mcp-ai-memory
   ```

### 数据备份

```bash
# Qdrant 数据备份
docker exec qdrant-vectordb tar -czf - /qdrant/storage > qdrant-backup.tar.gz

# 恢复备份
docker exec qdrant-vectordb tar -xzf - < qdrant-backup.tar.gz
```

### 升级步骤

1. **拉取最新代码**
   ```bash
   git pull origin main
   ```

2. **重建镜像**
   ```bash
   docker-compose build --no-cache mcp-ai-memory
   ```

3. **重新启动服务**
   ```bash
   docker-compose up -d mcp-ai-memory
   ```

4. **验证升级**
   ```bash
   docker-compose logs -f mcp-ai-memory
   ```

---

## 故障排查

### 问题 1：Qdrant 连接失败

```
Error: Cannot connect to Qdrant at localhost:6333
```

**解决方案**：
```bash
# 检查 Qdrant 服务
docker ps | grep qdrant

# 检查 Qdrant 日志
docker logs qdrant-vectordb

# 重启 Qdrant
docker-compose restart qdrant
```

### 问题 2：文件锁冲突

```
RuntimeError: Storage folder is already accessed by another instance
```

**解决方案**：
```bash
# 停止所有 Python 进程
pkill -f "mcp_ai_memory"

# 等待 2 秒
sleep 2

# 重启服务
docker-compose restart qdrant
```

### 问题 3：内存不足

**解决方案**：
```bash
# 增加 Docker 内存限制
docker update --memory 2g qdrant-vectordb

# 或在 docker-compose.yml 中修改
services:
  qdrant:
    mem_limit: 2g
```

---

## 性能调优

### Qdrant 优化

```env
# 增加向量缓存
QDRANT_CACHE_SIZE=100000

# 优化同步模式
QDRANT_SYNC_MODE=FSyncGrain
```

### MCP 服务优化

```env
# 增加工作进程（如使用 Gunicorn）
WORKERS=4

# 增加连接超时
CONNECTION_TIMEOUT=30

# 启用请求缓存
ENABLE_CACHE=true
```

---

## 最佳实践

1. ✅ 始终使用 Qdrant 服务（不用本地文件存储）
2. ✅ 定期备份数据
3. ✅ 监控服务日志
4. ✅ 使用环境变量管理敏感信息
5. ✅ 实施请求限流和认证
6. ✅ 定期升级依赖项
7. ✅ 使用专业的日志聚合工具
8. ✅ 配置 CI/CD 自动化部署

---

## 支持和反馈

遇到问题？
- 查看 [README.md](../README.md) 的故障排查部分
- 运行 `uv run python diagnose_api.py` 诊断工具
- 提交 Issue 到 GitHub 仓库

