---
name: project-memory-sync
description: 自动同步项目知识到长期记忆系统。当用户询问项目功能/设计（使用"熟悉"、"了解"、"本项目"等词汇），或修改了代码、接口、文档时，自动使用 MCP 记忆服务添加、更新或删除相关记忆。
---

# 项目记忆同步

本 Skill 让 Cursor Agent 自动管理项目知识的长期记忆，与 `mem0-local` MCP 服务配合使用。

## 触发条件

### 场景 A：用户询问项目信息

检测以下关键词或意图：

- "熟悉"、"了解"、"介绍"
- "本项目"、"这个项目"、"当前项目"
- "功能"、"设计"、"架构"、"实现"
- "怎么工作"、"如何实现"、"是什么"

**动作**：先搜索记忆获取已有知识，结合代码分析回答用户。

### 场景 B：代码/文档变更

检测以下行为：

- 修改了核心代码文件（非测试/配置）
- 新增/删除/重命名接口或函数
- 修改了 README、DESIGN、SPEC 等文档
- 变更了 API 定义、Proto、Schema

**动作**：将变更内容同步到记忆系统。

## 操作流程

### 1. 查询项目信息时

```text
步骤 0: 确定目标项目
→ 如果用户明确指定了项目名 → 直接使用
→ 如果在项目工作区且用户说"本项目" → 使用当前项目名
→ 如果无法确定 → 询问用户要搜索哪个项目

步骤 1: 搜索已有记忆（需完整分页）
→ 调用 search_memories(query="功能/设计/架构", filters={"project": "项目名"}, limit=20, offset=0)
→ 必须使用 filters 参数按项目过滤
→ ⚠️ 检查返回的 has_more 字段，如果为 true 则继续分页查询
→ 重复调用 offset += 20 直到 has_more=false，确保获取完整结果

步骤 2: 分析代码库
→ 阅读相关源码，理解当前实现

步骤 3: 整合回答
→ 结合记忆 + 代码分析，回答用户问题

步骤 4: 补充记忆（如发现新知识）
→ 调用 add_memory 保存新发现的重要信息
```

### 2. 修改代码/文档后

```text
步骤 1: 分析变更内容
→ 识别：新增功能 / 修改功能 / 删除功能

步骤 2: 搜索相关记忆（需完整分页）
→ 调用 search_memories(query="变更相关的功能/模块名", filters={"project": "项目名"})
→ 必须使用 filters 参数按项目过滤，避免影响其他项目的记忆
→ ⚠️ 必须分页查询直到 has_more=false，确保找到所有相关记忆再操作

步骤 3: 选择操作

如果是【新增功能】：
  → add_memory(text="[项目名] 新增了 [功能描述]", metadata={"project": "项目名", ...})

如果是【修改功能】：
  → 找到相关记忆 ID（从完整分页结果中筛选）
  → update_memory(memory_id="xxx", text="[更新后的描述]")

如果是【删除功能】：
  → 找到相关记忆 ID（从完整分页结果中筛选）
  → delete_memory(memory_id="xxx")

步骤 4: 确认同步
→ 告知用户记忆已更新
```

## MCP 工具使用指南

> **注意**：以下示例中的 `server: "mem0-local"` 是推荐的服务器名称。实际使用时，请根据你的 MCP 配置文件（`~/.cursor/mcp.json` 或项目级配置）中定义的服务器名称进行调整。

### 添加记忆

```json
// 保存新功能/新知识
{
  "tool": "add_memory",
  "server": "mem0-local",
  "arguments": {
    "text": "[项目名] [功能模块]: [具体描述]",
    "metadata": {
      "type": "project_knowledge",
      "project": "项目名称",
      "category": "feature|design|api|config"
    }
  }
}
```

**记忆文本格式建议**：

- `[项目名] 核心功能: ...`
- `[项目名] API接口: ...`
- `[项目名] 设计决策: ...`
- `[项目名] 配置说明: ...`

### 搜索记忆

> **重要**：搜索时**必须**使用 `filters` 参数指定项目名进行过滤，确保只搜索目标项目的记忆！

```json
// 查找相关记忆（推荐方式：使用 filters 过滤项目）
{
  "tool": "search_memories",
  "server": "mem0-local",
  "arguments": {
    "query": "具体要查找的内容",
    "filters": {
      "project": "项目名称"
    },
    "limit": 20
  }
}
```

**分页参数说明**：

- `limit`：每页返回的最大结果数，默认 20
- `offset`：跳过的结果数，用于分页，默认 0
- 返回结果中包含 `has_more` 字段，表示是否还有更多结果

**分页返回格式**：

```json
{
  "results": [...],
  "count": 20,
  "offset": 0,
  "limit": 20,
  "has_more": true
}
```

**⚠️ 获取完整结果的重要规则**：

当需要查找所有相关记忆时（如：更新/删除前确认、全面了解项目信息），**必须循环分页直到 `has_more=false`**：

```text
步骤 1: 首次搜索
→ search_memories(query="...", filters={...}, limit=20, offset=0)
→ 检查返回的 has_more

步骤 2: 如果 has_more=true，继续获取下一页
→ search_memories(query="...", filters={...}, limit=20, offset=20)
→ 累积结果，再次检查 has_more

步骤 3: 重复直到 has_more=false
→ 合并所有页的结果
```

**分页查询示例**：

```json
// 第一页
{
  "query": "核心功能",
  "filters": {"project": "mcp-ai-memory"},
  "limit": 20,
  "offset": 0
}

// 第二页（如果 has_more=true）
{
  "query": "核心功能",
  "filters": {"project": "mcp-ai-memory"},
  "limit": 20,
  "offset": 20
}
```

**filters 参数说明**：

- `filters` 支持按 metadata 字段过滤，最常用的是按 `project` 过滤
- ⚠️ **重要兼容性说明（Cursor 常见踩坑）**：
  - mem0 的 `Memory.search()` 文档里描述了 `eq/ne/in/...` 等“增强 filters”，但 **在 mem0 1.0.3 + Qdrant 向量库实现中**，Qdrant 的过滤器构造只支持：
    - **标量等值匹配**：`{"project": "xxx"}`
    - **范围查询（仅 gte/lte 组合）**：`{"some_number": {"gte": 1, "lte": 10}}`
  - 其他 dict 结构（例如 `{"project": {"in": [...]}}` / `{"project": {"eq": ...}}` / `{"project": {"ne": ...}}`）会被当成 “MatchValue.value=一个 dict” 传入，从而触发 pydantic 校验错误（你看到的 `MatchValue` validation error）。
  - 因此在本项目中，**不要让 Cursor 发起**上述 dict 操作符写法；推荐只使用 **精确匹配**（标量）：`{"project": "mcp-ai-memory"}`

**多项目过滤的正确方式（替代 `in`）**：

- 需要查多个项目时，使用“**多次调用 + 合并结果**”：
  - 对每个项目分别调用 `search_memories(query=..., filters={"project": "<name>"}, limit=..., offset=0)`
  - 分页取全（检查 `has_more`，offset += limit）
  - 将多次返回的 `results` 合并后再做去重/排序（按需要在 Agent 侧处理）

**正确示例**：

```json
// 搜索 mcp-ai-memory 项目的核心功能
{
  "query": "核心功能",
  "filters": {"project": "mcp-ai-memory"},
  "limit": 20
}
```

**错误示例**：

```json
// ❌ 缺少 filters，会搜到所有项目的记忆
{
  "query": "核心功能",
  "limit": 20
}

// ❌ 不要使用 dict 操作符写法（mem0 可能会校验失败）
// 如：{"project": {"in": ["proj1", "proj2"]}} / {"project": {"eq": "proj"}} / {"project": {"ne": "proj"}}

// ❌ 只取第一页就停止，可能遗漏重要记忆
// 当 has_more=true 时，必须继续分页查询！
```

### 确定项目名的策略

> **关键规则**：当不确定要搜索哪个项目时，**必须先询问用户**！

**判断是否需要询问用户**：

1. **无需询问**（可以自动确定项目名）：
   - 用户明确提到了项目名，如"搜索 mcp-ai-memory 的功能"
   - 当前正在某个项目的工作区中，且用户询问"本项目"、"这个项目"
   - 上下文中已经确定了目标项目

2. **必须询问**（无法确定项目名）：
   - 用户没有指定项目，如"帮我查一下之前的设计决策"
   - 用户可能涉及多个项目，如"查一下所有项目的配置方式"
   - 用户的问题模糊，不清楚是针对哪个项目

**询问用户的方式**：

```text
我需要搜索长期记忆来回答你的问题。请告诉我要搜索哪个项目的记忆？

可选：
1. 当前项目（[自动检测的项目名]）
2. 指定其他项目名
3. 搜索所有项目（不推荐，结果可能不精确）
```

**自动检测项目名的方法**：

- 从当前工作区路径提取项目目录名
- 从 `package.json`、`pyproject.toml`、`go.mod` 等配置文件读取项目名
- 从 `.git` 目录获取仓库名称

### 更新记忆

```json
// 修改已有记忆
{
  "tool": "update_memory",
  "server": "mem0-local",
  "arguments": {
    "memory_id": "从搜索结果获取",
    "text": "更新后的完整描述"
  }
}
```

### 删除记忆

```json
// 删除过时记忆
{
  "tool": "delete_memory",
  "server": "mem0-local",
  "arguments": {
    "memory_id": "从搜索结果获取"
  }
}
```

## 判断策略

### 何时添加记忆

- 新增了重要功能或模块
- 发现了项目的关键设计决策
- 用户明确要求记住某些信息
- 修复了重要 bug（记录问题和解决方案）

### 何时更新记忆

- 功能行为发生变化
- API 签名/参数修改
- 配置项变更
- 设计方案调整

### 何时删除记忆

- 功能被完全移除
- 记忆内容已过时且不再适用
- 用户明确要求删除

### 何时不操作

- 仅格式化代码、修复 typo
- 添加注释、调整空格
- 测试文件的变更
- 临时性的调试代码

## 记忆内容规范

### 有效的记忆示例

```text
✅ "mcp-ai-memory 项目使用 Mem0 库实现长期记忆存储，支持 Qdrant 和 pgvector 向量库"
✅ "mcp-ai-memory 的 add_memory 接口支持 text、messages、user_id、metadata 等参数"
✅ "项目支持 SSE 和 stdio 两种传输模式，通过 TRANSPORT 环境变量切换"
```

### 无效的记忆示例

```text
❌ "修改了代码"（太模糊）
❌ "添加了一些功能"（没有具体内容）
❌ "文件在 src/server.py"（仅位置信息，无实质内容）
```

## 注意事项

1. **避免重复**：添加前先搜索，避免重复记忆
2. **保持简洁**：每条记忆聚焦一个知识点
3. **包含上下文**：记忆中包含项目名，便于后续检索
4. **及时更新**：代码变更后主动更新相关记忆
5. **用户确认**：重要操作前可询问用户确认
6. **使用 filters 过滤项目**：搜索时必须使用 `filters={"project": "项目名"}` 过滤，确保只返回目标项目的记忆
7. **不确定时主动询问**：当无法确定要搜索哪个项目时，必须先询问用户项目名，不要猜测
8. **完整分页查询**：搜索时必须检查 `has_more` 字段，如果为 `true` 则继续分页查询（offset += limit），直到获取所有相关结果。不要只取第一页就停止！
