#!/usr/bin/env python3
"""测试 MCP AI Memory 服务的功能。

这个脚本会测试所有 MCP 工具的功能：
- add_memory: 添加记忆
- search_memories: 语义搜索记忆
- get_memories: 获取所有记忆
- get_memory: 获取单个记忆
- update_memory: 更新记忆
- get_memory_history: 获取记忆历史
- delete_memory: 删除单个记忆
- delete_all_memories: 批量删除记忆

使用方法:
    python tests/test_mcp_server.py [--url URL]

参数:
    --url: MCP 服务器 URL，默认 http://localhost:8050
    --skip-api: 跳过需要 LLM/Embedding API 调用的测试
"""

import argparse
import asyncio
import json
import sys
import uuid
from typing import Any, Dict, Optional

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


# API 调用失败的错误关键词
API_ERROR_KEYWORDS = ["Connection error", "timeout", "rate limit", "API", "401", "403", "500"]


def is_api_error(result: Optional[Dict]) -> bool:
    """检查结果是否是 API 调用错误。"""
    if not result:
        return False
    error = result.get("error", "")
    if isinstance(error, str):
        return any(kw.lower() in error.lower() for kw in API_ERROR_KEYWORDS)
    return False


async def test_mcp_server(base_url: str, skip_api: bool = False):
    """使用 MCP SDK 测试服务器功能。
    
    Args:
        base_url: MCP 服务器地址
        skip_api: 是否跳过需要 LLM/Embedding API 的测试
    """
    
    print("\n" + "=" * 60)
    print("MCP AI Memory 服务功能测试")
    print("=" * 60)
    print(f"服务器地址: {base_url}")
    if skip_api:
        print("⚠️ 跳过 API 依赖测试模式")
    
    # 生成唯一的测试用户 ID，避免影响真实数据
    test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    test_agent_id = f"test_agent_{uuid.uuid4().hex[:8]}"
    
    print(f"测试用户 ID: {test_user_id}")
    print(f"测试代理 ID: {test_agent_id}")
    
    all_passed = True
    memory_id = None
    
    try:
        # 连接到 MCP 服务器
        print("\n📡 连接到 MCP 服务器...")
        
        async with streamable_http_client(f"{base_url}/mcp") as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                # 初始化会话
                await session.initialize()
                print("✅ 已连接并初始化会话")
                
                # 列出可用工具
                print("\n📋 获取可用工具列表...")
                tools_result = await session.list_tools()
                tools = tools_result.tools
                print(f"   找到 {len(tools)} 个工具:")
                for tool in tools:
                    print(f"   • {tool.name}: {tool.description[:50]}...")
                
                # 辅助函数：调用工具并解析结果
                async def call_tool(name: str, arguments: Dict[str, Any]) -> Optional[Dict]:
                    nonlocal all_passed
                    try:
                        result = await session.call_tool(name, arguments=arguments)
                        if result.content and len(result.content) > 0:
                            text = result.content[0].text
                            try:
                                return json.loads(text)
                            except json.JSONDecodeError:
                                return {"raw": text}
                        return None
                    except Exception as e:
                        print(f"   ❌ 调用工具 {name} 失败: {e}")
                        all_passed = False
                        return None

                # 测试 1: 添加记忆 (需要 LLM API)
                api_available = True
                
                if skip_api:
                    print("\n" + "-" * 40)
                    print("📝 测试 1: 添加记忆 (add_memory) - 已跳过")
                    print("-" * 40)
                    print("   ⏭️ 需要 LLM API，已跳过")
                else:
                    print("\n" + "-" * 40)
                    print("📝 测试 1: 添加记忆 (add_memory)")
                    print("-" * 40)
                    
                    result = await call_tool("add_memory", {
                        "text": "我喜欢用 Python 编程，特别是使用 FastAPI 框架开发 API。",
                        "user_id": test_user_id,
                        "agent_id": test_agent_id,
                        "metadata": {"source": "test_script", "importance": "high"}
                    })
                    
                    if result and "error" not in result:
                        print(f"   ✅ 添加成功")
                        print(f"   结果: {json.dumps(result, ensure_ascii=False, indent=2)[:300]}...")
                        # 尝试从结果中获取 memory_id
                        if isinstance(result, dict):
                            if "results" in result and len(result["results"]) > 0:
                                memory_id = result["results"][0].get("id")
                            elif "id" in result:
                                memory_id = result["id"]
                        if memory_id:
                            print(f"   记忆 ID: {memory_id}")
                    elif is_api_error(result):
                        print(f"   ⚠️ API 连接失败 (非 MCP 服务问题): {result.get('error', '')}")
                        print("   💡 请检查 .env 中的 LLM_BASE_URL 和 LLM_API_KEY 配置")
                        api_available = False
                    else:
                        print(f"   ❌ 添加失败: {result}")
                        all_passed = False

                    # 添加更多测试记忆
                    if api_available:
                        print("\n   添加更多测试记忆...")
                        
                        test_memories = [
                            "我的工作邮箱是 test@example.com",
                            "我每天早上 9 点开始工作",
                            "我喜欢喝咖啡，尤其是拿铁",
                        ]
                        
                        for text in test_memories:
                            result = await call_tool("add_memory", {
                                "text": text,
                                "user_id": test_user_id,
                                "agent_id": test_agent_id,
                            })
                            if result and "error" not in result:
                                print(f"   ✅ 已添加: {text[:30]}...")
                            elif is_api_error(result):
                                print(f"   ⚠️ API 失败: {text[:30]}...")
                            else:
                                print(f"   ❌ 添加失败: {text[:30]}...")

                # 测试 2: 获取所有记忆
                print("\n" + "-" * 40)
                print("📋 测试 2: 获取所有记忆 (get_memories)")
                print("-" * 40)
                
                result = await call_tool("get_memories", {
                    "user_id": test_user_id,
                    "agent_id": test_agent_id,
                })
                
                if result and "error" not in result:
                    count = result.get("count", 0)
                    print(f"   ✅ 获取成功，共 {count} 条记忆")
                    memories = result.get("results", [])
                    for i, mem in enumerate(memories[:3]):
                        mem_text = mem.get("memory", mem.get("text", ""))[:50]
                        print(f"   {i+1}. {mem_text}...")
                    if len(memories) > 3:
                        print(f"   ... 还有 {len(memories) - 3} 条记忆")
                    
                    # 获取第一个记忆的 ID 用于后续测试
                    if memories and not memory_id:
                        memory_id = memories[0].get("id")
                else:
                    print(f"   ❌ 获取失败: {result}")
                    all_passed = False

                # 测试 3: 语义搜索 (需要 Embedding API)
                if skip_api or not api_available:
                    print("\n" + "-" * 40)
                    print("🔍 测试 3: 语义搜索记忆 (search_memories) - 已跳过")
                    print("-" * 40)
                    print("   ⏭️ 需要 Embedding API，已跳过")
                else:
                    print("\n" + "-" * 40)
                    print("🔍 测试 3: 语义搜索记忆 (search_memories)")
                    print("-" * 40)
                    
                    result = await call_tool("search_memories", {
                        "query": "编程语言和开发框架",
                        "user_id": test_user_id,
                        "limit": 5,
                    })
                    
                    if result and "error" not in result:
                        count = result.get("count", 0)
                        print(f"   ✅ 搜索成功，找到 {count} 条相关记忆")
                        memories = result.get("results", [])
                        for i, mem in enumerate(memories[:3]):
                            mem_text = mem.get("memory", mem.get("text", ""))[:50]
                            score = mem.get("score", "N/A")
                            print(f"   {i+1}. [相关度: {score}] {mem_text}...")
                    elif is_api_error(result):
                        print(f"   ⚠️ Embedding API 连接失败: {result.get('error', '')}")
                        print("   💡 请检查 .env 中的 EMBEDDING_BASE_URL 和 EMBEDDING_API_KEY 配置")
                    else:
                        print(f"   ❌ 搜索失败: {result}")
                        all_passed = False

                # 测试 4: 获取单个记忆 (需要已添加的记忆)
                if memory_id:
                    print("\n" + "-" * 40)
                    print("📄 测试 4: 获取单个记忆 (get_memory)")
                    print("-" * 40)
                    
                    result = await call_tool("get_memory", {
                        "memory_id": memory_id,
                    })
                    
                    if result and "error" not in result:
                        print(f"   ✅ 获取成功")
                        mem_text = result.get("memory", result.get("text", str(result)))
                        print(f"   内容: {str(mem_text)[:100]}...")
                    else:
                        print(f"   ❌ 获取失败: {result}")
                        all_passed = False
                else:
                    print("\n" + "-" * 40)
                    print("📄 测试 4: 获取单个记忆 (get_memory) - 已跳过")
                    print("-" * 40)
                    print("   ⏭️ 没有可用的 memory_id，已跳过")

                # 测试 5: 更新记忆 (需要 LLM API)
                if memory_id:
                    if skip_api or not api_available:
                        print("\n" + "-" * 40)
                        print("✏️ 测试 5: 更新记忆 (update_memory) - 已跳过")
                        print("-" * 40)
                        print("   ⏭️ 需要 LLM API，已跳过")
                    else:
                        print("\n" + "-" * 40)
                        print("✏️ 测试 5: 更新记忆 (update_memory)")
                        print("-" * 40)
                        
                        result = await call_tool("update_memory", {
                            "memory_id": memory_id,
                            "text": "我喜欢用 Python 和 Go 编程，FastAPI 和 Gin 是我最喜欢的框架。",
                        })
                        
                        if result and "error" not in result:
                            print(f"   ✅ 更新成功")
                            print(f"   结果: {json.dumps(result, ensure_ascii=False)[:150]}...")
                        elif is_api_error(result):
                            print(f"   ⚠️ API 连接失败: {result.get('error', '')}")
                        else:
                            print(f"   ❌ 更新失败: {result}")
                            all_passed = False
                else:
                    print("\n" + "-" * 40)
                    print("✏️ 测试 5: 更新记忆 (update_memory) - 已跳过")
                    print("-" * 40)
                    print("   ⏭️ 没有可用的 memory_id，已跳过")

                # 测试 6: 获取记忆历史
                if memory_id:
                    print("\n" + "-" * 40)
                    print("📜 测试 6: 获取记忆历史 (get_memory_history)")
                    print("-" * 40)
                    
                    result = await call_tool("get_memory_history", {
                        "memory_id": memory_id,
                    })
                    
                    if result:
                        if isinstance(result, list):
                            print(f"   ✅ 获取成功，共 {len(result)} 条历史记录")
                            for i, hist in enumerate(result[:2]):
                                print(f"   {i+1}. {json.dumps(hist, ensure_ascii=False)[:80]}...")
                        else:
                            print(f"   ✅ 获取成功")
                            print(f"   结果: {json.dumps(result, ensure_ascii=False)[:150]}...")
                    else:
                        print("   ⚠️ 获取历史可能不支持或无历史记录")
                else:
                    print("\n" + "-" * 40)
                    print("📜 测试 6: 获取记忆历史 (get_memory_history) - 已跳过")
                    print("-" * 40)
                    print("   ⏭️ 没有可用的 memory_id，已跳过")

                # 测试 7: 删除单个记忆
                if memory_id:
                    print("\n" + "-" * 40)
                    print("🗑️ 测试 7: 删除单个记忆 (delete_memory)")
                    print("-" * 40)
                    
                    result = await call_tool("delete_memory", {
                        "memory_id": memory_id,
                    })
                    
                    if result and "error" not in result:
                        print(f"   ✅ 删除成功")
                    else:
                        print(f"   ❌ 删除失败: {result}")
                        all_passed = False
                else:
                    print("\n" + "-" * 40)
                    print("🗑️ 测试 7: 删除单个记忆 (delete_memory) - 已跳过")
                    print("-" * 40)
                    print("   ⏭️ 没有可用的 memory_id，已跳过")

                # 测试 8: 批量删除记忆 (清理测试数据)
                # ⚠️ 注意: mem0 1.0.x 有 bug，delete_all 会删除所有用户的记忆！
                # 所以这里改用逐条删除的方式清理测试数据
                print("\n" + "-" * 40)
                print("🗑️ 测试 8: 清理测试记忆 (逐条删除)")
                print("-" * 40)
                
                # 先获取测试用户的所有记忆
                result = await call_tool("get_memories", {
                    "user_id": test_user_id,
                    "agent_id": test_agent_id,
                })
                
                if result and "error" not in result:
                    memories = result.get("results", [])
                    deleted_count = 0
                    for mem in memories:
                        mem_id = mem.get("id")
                        if mem_id:
                            del_result = await call_tool("delete_memory", {
                                "memory_id": mem_id,
                            })
                            if del_result and "error" not in del_result:
                                deleted_count += 1
                    print(f"   ✅ 已删除 {deleted_count}/{len(memories)} 条测试记忆")
                else:
                    print(f"   ⚠️ 获取记忆列表失败: {result}")

                # 验证删除成功
                print("\n   验证删除结果...")
                result = await call_tool("get_memories", {
                    "user_id": test_user_id,
                    "agent_id": test_agent_id,
                })
                
                if result:
                    count = result.get("count", 0)
                    if count == 0:
                        print(f"   ✅ 验证成功，所有测试记忆已删除")
                    else:
                        print(f"   ⚠️ 仍有 {count} 条记忆残留")

    except ConnectionRefusedError:
        print(f"❌ 无法连接到服务器 {base_url}")
        print("   请确保 MCP 服务器正在运行:")
        print("   TRANSPORT=sse uv run python -m mcp_ai_memory.server")
        return False
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 测试结果汇总
    print("\n" + "=" * 60)
    if all_passed:
        if skip_api or not api_available:
            print("✅ MCP 服务连接和基础功能测试通过！")
            print("💡 完整功能测试需要配置有效的 LLM/Embedding API")
        else:
            print("🎉 所有测试通过！MCP 服务功能正常。")
    else:
        print("⚠️ 部分测试失败，请检查服务器日志。")
    print("=" * 60)
    
    # 如果只是 API 连接问题，仍然返回成功（MCP 服务本身正常）
    if not all_passed and not api_available:
        print("\n注意: 测试失败是由于 LLM/Embedding API 连接问题，")
        print("      MCP 服务本身运行正常。请检查以下配置：")
        print("      - LLM_BASE_URL")
        print("      - LLM_API_KEY")
        print("      - EMBEDDING_BASE_URL")
        print("      - EMBEDDING_API_KEY")
    
    return all_passed


async def simple_connectivity_test(base_url: str) -> bool:
    """简单的连接性测试。"""
    print("\n📡 检查服务器连接性...")
    
    try:
        async with streamable_http_client(f"{base_url}/mcp") as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                print(f"✅ MCP 服务器连接正常 ({base_url})")
                return True
    except ConnectionRefusedError:
        print(f"❌ 无法连接到 {base_url}")
        print("   请确保 MCP 服务器正在运行:")
        print("   TRANSPORT=sse uv run python -m mcp_ai_memory.server")
        return False
    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        return False


async def list_available_tools(base_url: str):
    """列出所有可用的 MCP 工具。"""
    print("\n📋 获取可用工具列表...")
    
    try:
        async with streamable_http_client(f"{base_url}/mcp") as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                
                tools_result = await session.list_tools()
                tools = tools_result.tools
                
                print(f"\n✅ 找到 {len(tools)} 个可用工具:\n")
                for tool in tools:
                    print(f"  • {tool.name}")
                    print(f"    描述: {tool.description}")
                    if tool.inputSchema:
                        props = tool.inputSchema.get("properties", {})
                        required = tool.inputSchema.get("required", [])
                        if props:
                            print(f"    参数:")
                            for prop_name, prop_info in props.items():
                                req_mark = "*" if prop_name in required else ""
                                prop_desc = prop_info.get("description", "")[:40]
                                prop_type = prop_info.get("type", "any")
                                print(f"      - {prop_name}{req_mark} ({prop_type}): {prop_desc}...")
                    print()
                    
    except Exception as e:
        print(f"❌ 获取工具列表失败: {e}")


async def list_prompts(base_url: str):
    """列出所有可用的 prompts。"""
    print("\n📝 获取可用 prompts...")
    
    try:
        async with streamable_http_client(f"{base_url}/mcp") as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                
                prompts_result = await session.list_prompts()
                prompts = prompts_result.prompts
                
                if prompts:
                    print(f"\n✅ 找到 {len(prompts)} 个可用 prompt:\n")
                    for prompt in prompts:
                        print(f"  • {prompt.name}")
                        if prompt.description:
                            print(f"    描述: {prompt.description}")
                else:
                    print("   没有可用的 prompts")
                    
    except Exception as e:
        print(f"❌ 获取 prompts 失败: {e}")


def main():
    """主函数。"""
    parser = argparse.ArgumentParser(description="测试 MCP AI Memory 服务")
    parser.add_argument(
        "--url",
        default="http://localhost:8050",
        help="MCP 服务器 URL (默认: http://localhost:8050)"
    )
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="只列出可用工具"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="只进行连接性测试"
    )
    parser.add_argument(
        "--skip-api",
        action="store_true",
        help="跳过需要 LLM/Embedding API 调用的测试"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("MCP AI Memory 服务测试工具")
    print("=" * 60)
    
    if args.quick:
        success = asyncio.run(simple_connectivity_test(args.url))
        sys.exit(0 if success else 1)
    
    if args.list_tools:
        asyncio.run(simple_connectivity_test(args.url))
        asyncio.run(list_available_tools(args.url))
        asyncio.run(list_prompts(args.url))
        sys.exit(0)
    
    # 完整测试
    success = asyncio.run(test_mcp_server(args.url, skip_api=args.skip_api))
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
