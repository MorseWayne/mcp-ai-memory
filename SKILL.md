---
name: project-memory-sync
description: 自动同步项目知识到长期记忆系统。当用户询问项目功能/设计，或修改了代码、接口、文档时，自动使用 MCP 记忆服务管理相关记忆。
version: 1.1.0
category: memory-management
---

# AI 助手项目记忆同步指南 (Universal Agent Memory Skill)

本指南旨在指导 AI 助手（如 Claude, Cursor, Windsurf 等）如何高效、准确地利用 `mcp-ai-memory` 服务管理项目的长期记忆。

## 核心目标
- **自动化同步**：在代码变更、架构调整或文档更新时，自动同步知识到记忆系统。
- **项目级隔离**：通过 `project` 标签确保多项目记忆互不干扰。
- **高质量检索**：利用语义搜索和重排序，在开启新对话时快速找回项目上下文。

---

## 触发场景

### 场景 A：知识检索（主动学习）
当用户提问涉及“项目架构”、“如何实现”、“功能介绍”或“历史背景”时。
**动作**：
1.  调用 `search_memories` 检索相关记忆。
2.  结合记忆内容与当前源码进行深度分析。

### 场景 B：知识同步（被动更新）
当 AI 完成以下操作后：
- 修改了核心逻辑、API 接口或数据模型。
- 更新了 README 或技术文档。
- 解决了复杂的 Bug（记录解决方案）。
**动作**：
1.  根据变更内容提取核心事实。
2.  更新或添加对应的长期记忆。

---

## 工具调用最佳实践

### 1. 语义搜索 (search_memories)
搜索时必须遵循以下规则：
- **强制过滤**：务必带上 `filters={"project": "项目名"}`，避免混入其他项目的干扰信息。
- **阈值控制**：建议设置 `threshold: 0.6`（或根据需求调整），过滤掉无关的低分结果。
- **启用重排序**：保持 `rerank: true` 以获取最准确的排序。
- **完整分页**：检查 `has_more` 字段。如果为 `true`，必须循环增加 `offset` 直到获取所有相关知识点。

```json
{
  "tool": "search_memories",
  "arguments": {
    "query": "项目核心架构与技术栈",
    "filters": {"project": "my-awesome-project"},
    "threshold": 0.65,
    "rerank": true,
    "limit": 20
  }
}
```

### 2. 存入记忆 (add_memory)
- **去重检查**：在 `add_memory` 之前，先进行一次 `search_memories`。如果发现已有极其相似的记录，应优先使用 `update_memory` 而非重复添加。
- **元数据规范**：
    - `project`: (必须) 唯一的项目标识。
    - `type`: (建议) 如 `feature`, `architecture`, `api`, `convention`。

```json
{
  "tool": "add_memory",
  "arguments": {
    "text": "本项目使用 FastAPI 作为 Web 框架，采用异步驱动架构。",
    "metadata": {
      "project": "my-awesome-project",
      "type": "architecture"
    }
  }
}
```

### 3. 安全批量删除 (delete_all_memories)
本服务的 `delete_all_memories` 已针对 Qdrant 的过滤 Bug 进行了加固（内部执行“查 ID 后逐条删除”）。
- **慎用**：仅在项目彻底移除或用户要求重置项目记忆时使用。
- **必须带参数**：调用时必须提供 `user_id` 或 `filters` 相关参数，严禁无参数调用。

---

## 记忆提取规范（Fact Extraction）

好的记忆应该是**自包含**且**原子化**的：
- ✅ "mcp-ai-memory 支持 Streamable HTTP 传输协议。"
- ❌ "它支持这个协议。" (缺少主体)
- ✅ "项目 API 密钥通过环境变量 LLM_API_KEY 配置。"
- ❌ "修改了配置方式。" (太模糊)

---

## AI 助手决策逻辑

1. **收到任务** -> 检查是否有项目上下文。
2. **缺失上下文** -> 调用 `search_memories(filters={"project": "..."})` 获取背景。
3. **执行代码修改** -> 任务完成后，分析修改了哪些关键知识。
4. **同步变更** ->
   - 如果是新知识 -> `add_memory`
   - 如果是旧知识更新 -> `update_memory`
   - 如果功能已废弃 -> `delete_memory`
5. **告知用户** -> “我已将本次架构变更同步到长期记忆中。”
