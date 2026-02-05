#!/usr/bin/env python3
"""测试 Mem0 + Qdrant 的 Filter 操作符支持情况。

根据 https://docs.mem0.ai/open-source/features/metadata-filtering 文档，
Mem0 1.0.0+ 声称支持以下操作符：
- 比较操作符: eq, ne, gt, gte, lt, lte
- 列表操作符: in, nin
- 字符串操作符: contains, icontains
- 通配符: *
- 逻辑操作符: AND, OR, NOT

此测试文件用于验证这些操作符在 Qdrant 后端的实际支持情况。
"""

import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# 加载 .env
env_path = Path(__file__).parent / ".env"
if not env_path.exists():
    env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_ai_memory.config import create_mem0_client


def print_header(title: str):
    """打印标题。"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_section(title: str):
    """打印小节标题。"""
    print(f"\n--- {title} ---")


def print_result(name: str, success: bool, message: str = ""):
    """打印测试结果。"""
    status = "✅" if success else "❌"
    msg = f" - {message}" if message else ""
    print(f"  {status} {name}{msg}")


class QdrantFilterTest:
    """Qdrant Filter 操作符测试类。"""
    
    def __init__(self):
        self.client = None
        self.test_user_id = f"filter_test_{os.getpid()}_{int(time.time())}"
        self.test_results: Dict[str, Dict[str, Any]] = {}
        
    def setup(self) -> bool:
        """初始化测试环境。"""
        print_section("初始化")
        try:
            self.client = create_mem0_client()
            print_result("创建 Mem0 客户端", True)
            return True
        except Exception as e:
            print_result("创建 Mem0 客户端", False, str(e))
            traceback.print_exc()
            return False
    
    def add_test_memories(self) -> bool:
        """添加测试记忆数据。"""
        print_section("添加测试记忆")
        
        # 测试数据 - 包含各种 metadata 用于过滤测试
        test_data = [
            {
                "content": "Python 是我最喜欢的编程语言",
                "metadata": {
                    "category": "programming",
                    "language": "python",
                    "priority": 10,
                    "is_active": True,
                    "tags": "backend,ai",
                }
            },
            {
                "content": "JavaScript 用于前端开发",
                "metadata": {
                    "category": "programming",
                    "language": "javascript",
                    "priority": 8,
                    "is_active": True,
                    "tags": "frontend,web",
                }
            },
            {
                "content": "Rust 是系统级编程语言",
                "metadata": {
                    "category": "programming",
                    "language": "rust",
                    "priority": 7,
                    "is_active": False,
                    "tags": "systems,performance",
                }
            },
            {
                "content": "喜欢阅读技术书籍",
                "metadata": {
                    "category": "hobby",
                    "priority": 5,
                    "is_active": True,
                    "tags": "reading,learning",
                }
            },
            {
                "content": "每天运动30分钟",
                "metadata": {
                    "category": "health",
                    "priority": 9,
                    "is_active": True,
                    "tags": "exercise,daily",
                }
            },
        ]
        
        try:
            for i, item in enumerate(test_data):
                result = self.client.add(
                    messages=[{"role": "user", "content": item["content"]}],
                    user_id=self.test_user_id,
                    metadata=item["metadata"],
                )
                print_result(f"添加记忆 {i+1}: {item['content'][:30]}...", True)
            
            # 等待索引
            print("  ⏳ 等待索引更新...")
            time.sleep(2)
            return True
            
        except Exception as e:
            print_result("添加测试记忆", False, str(e))
            traceback.print_exc()
            return False
    
    def test_filter(
        self, 
        name: str, 
        filters: Dict[str, Any],
        operator_type: str,
        expected_min_results: int = 0
    ) -> Dict[str, Any]:
        """测试单个过滤器。"""
        result = {
            "name": name,
            "operator_type": operator_type,
            "filters": filters,
            "success": False,
            "error": None,
            "results_count": 0,
            "results": [],
        }
        
        try:
            search_result = self.client.search(
                query="编程语言或爱好",  # 通用查询以匹配多条记忆
                user_id=self.test_user_id,
                filters=filters,
                limit=10,
            )
            
            # 处理结果
            if isinstance(search_result, dict) and "results" in search_result:
                memories = search_result.get("results", [])
            elif isinstance(search_result, list):
                memories = search_result
            else:
                memories = []
            
            result["success"] = True
            result["results_count"] = len(memories)
            result["results"] = [
                {
                    "memory": m.get("memory", ""),
                    "metadata": m.get("metadata", {}),
                }
                for m in memories[:3]  # 只保留前3条用于显示
            ]
            
            return result
            
        except Exception as e:
            result["error"] = str(e)
            result["error_type"] = type(e).__name__
            return result
    
    def run_all_tests(self):
        """运行所有过滤器测试。"""
        
        # ============================================================
        # 1. 基础过滤器 - 简单等值匹配
        # ============================================================
        print_header("1. 基础过滤器 - 简单等值匹配")
        
        basic_tests = [
            ("简单字符串匹配", {"category": "programming"}, "scalar_match"),
            ("简单布尔匹配", {"is_active": True}, "scalar_match"),
            ("简单数字匹配", {"priority": 10}, "scalar_match"),
        ]
        
        for name, filters, op_type in basic_tests:
            result = self.test_filter(name, filters, op_type)
            self.test_results[name] = result
            if result["success"]:
                print_result(name, True, f"返回 {result['results_count']} 条结果")
            else:
                print_result(name, False, result.get("error", "未知错误"))
        
        # ============================================================
        # 2. 比较操作符 - eq, ne, gt, gte, lt, lte
        # ============================================================
        print_header("2. 比较操作符 - eq, ne, gt, gte, lt, lte")
        
        comparison_tests = [
            ("eq - 等于", {"category": {"eq": "programming"}}, "eq"),
            ("ne - 不等于", {"category": {"ne": "programming"}}, "ne"),
            ("gt - 大于", {"priority": {"gt": 7}}, "gt"),
            ("gte - 大于等于", {"priority": {"gte": 8}}, "gte"),
            ("lt - 小于", {"priority": {"lt": 8}}, "lt"),
            ("lte - 小于等于", {"priority": {"lte": 7}}, "lte"),
        ]
        
        for name, filters, op_type in comparison_tests:
            result = self.test_filter(name, filters, op_type)
            self.test_results[name] = result
            if result["success"]:
                print_result(name, True, f"返回 {result['results_count']} 条结果")
            else:
                print_result(name, False, result.get("error", "未知错误")[:80])
        
        # ============================================================
        # 3. 范围查询 - gte + lte 组合
        # ============================================================
        print_header("3. 范围查询 - gte + lte 组合")
        
        range_tests = [
            ("范围查询 gte+lte", {"priority": {"gte": 5, "lte": 9}}, "range"),
        ]
        
        for name, filters, op_type in range_tests:
            result = self.test_filter(name, filters, op_type)
            self.test_results[name] = result
            if result["success"]:
                print_result(name, True, f"返回 {result['results_count']} 条结果")
            else:
                print_result(name, False, result.get("error", "未知错误")[:80])
        
        # ============================================================
        # 4. 列表操作符 - in, nin
        # ============================================================
        print_header("4. 列表操作符 - in, nin")
        
        list_tests = [
            ("in - 包含在列表中", {"category": {"in": ["programming", "hobby"]}}, "in"),
            ("nin - 不在列表中", {"category": {"nin": ["health"]}}, "nin"),
        ]
        
        for name, filters, op_type in list_tests:
            result = self.test_filter(name, filters, op_type)
            self.test_results[name] = result
            if result["success"]:
                print_result(name, True, f"返回 {result['results_count']} 条结果")
            else:
                print_result(name, False, result.get("error", "未知错误")[:80])
        
        # ============================================================
        # 5. 字符串操作符 - contains, icontains
        # ============================================================
        print_header("5. 字符串操作符 - contains, icontains")
        
        string_tests = [
            ("contains - 包含子串", {"tags": {"contains": "backend"}}, "contains"),
            ("icontains - 不区分大小写包含", {"tags": {"icontains": "BACKEND"}}, "icontains"),
        ]
        
        for name, filters, op_type in string_tests:
            result = self.test_filter(name, filters, op_type)
            self.test_results[name] = result
            if result["success"]:
                print_result(name, True, f"返回 {result['results_count']} 条结果")
            else:
                print_result(name, False, result.get("error", "未知错误")[:80])
        
        # ============================================================
        # 6. 通配符 - *
        # ============================================================
        print_header("6. 通配符 - * (字段存在)")
        
        wildcard_tests = [
            ("通配符 - 字段存在", {"language": "*"}, "wildcard"),
        ]
        
        for name, filters, op_type in wildcard_tests:
            result = self.test_filter(name, filters, op_type)
            self.test_results[name] = result
            if result["success"]:
                print_result(name, True, f"返回 {result['results_count']} 条结果")
            else:
                print_result(name, False, result.get("error", "未知错误")[:80])
        
        # ============================================================
        # 7. 逻辑操作符 - AND
        # ============================================================
        print_header("7. 逻辑操作符 - AND")
        
        and_tests = [
            ("AND - 多条件与", {
                "AND": [
                    {"category": "programming"},
                    {"is_active": True}
                ]
            }, "AND"),
            ("AND - 嵌套条件", {
                "AND": [
                    {"category": "programming"},
                    {"priority": {"gte": 8}}
                ]
            }, "AND_nested"),
        ]
        
        for name, filters, op_type in and_tests:
            result = self.test_filter(name, filters, op_type)
            self.test_results[name] = result
            if result["success"]:
                print_result(name, True, f"返回 {result['results_count']} 条结果")
            else:
                print_result(name, False, result.get("error", "未知错误")[:80])
        
        # ============================================================
        # 8. 逻辑操作符 - OR
        # ============================================================
        print_header("8. 逻辑操作符 - OR")
        
        or_tests = [
            ("OR - 多条件或", {
                "OR": [
                    {"category": "programming"},
                    {"category": "hobby"}
                ]
            }, "OR"),
        ]
        
        for name, filters, op_type in or_tests:
            result = self.test_filter(name, filters, op_type)
            self.test_results[name] = result
            if result["success"]:
                print_result(name, True, f"返回 {result['results_count']} 条结果")
            else:
                print_result(name, False, result.get("error", "未知错误")[:80])
        
        # ============================================================
        # 9. 逻辑操作符 - NOT
        # ============================================================
        print_header("9. 逻辑操作符 - NOT")
        
        not_tests = [
            ("NOT - 排除条件", {
                "NOT": [
                    {"category": "health"}
                ]
            }, "NOT"),
        ]
        
        for name, filters, op_type in not_tests:
            result = self.test_filter(name, filters, op_type)
            self.test_results[name] = result
            if result["success"]:
                print_result(name, True, f"返回 {result['results_count']} 条结果")
            else:
                print_result(name, False, result.get("error", "未知错误")[:80])
        
        # ============================================================
        # 10. 复杂嵌套逻辑
        # ============================================================
        print_header("10. 复杂嵌套逻辑")
        
        complex_tests = [
            ("复杂嵌套 - AND+OR+NOT", {
                "AND": [
                    {
                        "OR": [
                            {"category": "programming"},
                            {"category": "hobby"}
                        ]
                    },
                    {"is_active": True},
                    {
                        "NOT": [
                            {"priority": {"lt": 5}}
                        ]
                    }
                ]
            }, "complex_nested"),
        ]
        
        for name, filters, op_type in complex_tests:
            result = self.test_filter(name, filters, op_type)
            self.test_results[name] = result
            if result["success"]:
                print_result(name, True, f"返回 {result['results_count']} 条结果")
            else:
                print_result(name, False, result.get("error", "未知错误")[:80])
    
    def cleanup(self):
        """清理测试数据。
        
        ⚠️ 注意: mem0 1.0.x 有 bug，delete_all 会删除所有用户的记忆！
        所以这里改用逐条删除的方式清理测试数据。
        """
        print_section("清理测试数据")
        try:
            # 获取测试用户的所有记忆
            memories = self.client.get_all(user_id=self.test_user_id)
            if not memories:
                print_result("删除测试记忆", True, "没有需要删除的记忆")
                return
            
            # 逐条删除
            deleted_count = 0
            for mem in memories:
                mem_id = mem.get("id")
                if mem_id:
                    try:
                        self.client.delete(memory_id=mem_id)
                        deleted_count += 1
                    except Exception as e:
                        print_result(f"删除记忆 {mem_id}", False, str(e))
            
            print_result("删除测试记忆", True, f"已删除 {deleted_count}/{len(memories)} 条")
        except Exception as e:
            print_result("删除测试记忆", False, str(e))
    
    def print_summary(self):
        """打印测试摘要。"""
        print_header("测试摘要")
        
        # 按操作符类型分组
        operator_groups = {}
        for name, result in self.test_results.items():
            op_type = result.get("operator_type", "unknown")
            if op_type not in operator_groups:
                operator_groups[op_type] = {"pass": 0, "fail": 0, "tests": []}
            
            if result["success"]:
                operator_groups[op_type]["pass"] += 1
            else:
                operator_groups[op_type]["fail"] += 1
            operator_groups[op_type]["tests"].append((name, result))
        
        # 打印摘要表格
        print("\n操作符支持情况:")
        print("-" * 60)
        print(f"{'操作符类型':<20} {'通过':<10} {'失败':<10} {'状态':<10}")
        print("-" * 60)
        
        total_pass = 0
        total_fail = 0
        
        for op_type, stats in operator_groups.items():
            status = "✅ 支持" if stats["fail"] == 0 else "❌ 不支持"
            print(f"{op_type:<20} {stats['pass']:<10} {stats['fail']:<10} {status:<10}")
            total_pass += stats["pass"]
            total_fail += stats["fail"]
        
        print("-" * 60)
        print(f"{'总计':<20} {total_pass:<10} {total_fail:<10}")
        print()
        
        # 打印失败详情
        failed_tests = [
            (name, result) 
            for name, result in self.test_results.items() 
            if not result["success"]
        ]
        
        if failed_tests:
            print("\n失败的测试详情:")
            print("-" * 60)
            for name, result in failed_tests:
                print(f"\n❌ {name}")
                print(f"   过滤器: {result['filters']}")
                print(f"   错误类型: {result.get('error_type', 'Unknown')}")
                print(f"   错误信息: {result.get('error', 'N/A')[:200]}")
        
        # 打印成功的测试
        passed_tests = [
            (name, result) 
            for name, result in self.test_results.items() 
            if result["success"]
        ]
        
        if passed_tests:
            print("\n成功的测试:")
            print("-" * 60)
            for name, result in passed_tests:
                print(f"✅ {name}: 返回 {result['results_count']} 条结果")
        
        # 最终结论
        print("\n" + "=" * 60)
        if total_fail == 0:
            print("🎉 所有操作符都受支持！Qdrant 完全兼容 Mem0 增强过滤器。")
        else:
            print(f"⚠️  {total_fail} 个测试失败。部分操作符在 Qdrant 上不受支持。")
            print("\n建议:")
            print("  1. 使用简单标量匹配替代复杂操作符")
            print("  2. 范围查询使用 gte/lte 组合")
            print("  3. 避免使用 in/nin、contains、逻辑操作符")
        print("=" * 60)


def main():
    """主函数。"""
    print_header("Mem0 + Qdrant Filter 操作符验证测试")
    
    print("\n配置信息:")
    print(f"  向量库: {os.getenv('VECTOR_STORE_PROVIDER', 'qdrant')}")
    print(f"  Qdrant 路径: {os.getenv('QDRANT_PATH', 'N/A')}")
    print(f"  Qdrant 主机: {os.getenv('QDRANT_HOST', 'N/A')}")
    print(f"  LLM 提供商: {os.getenv('LLM_PROVIDER', 'openai')}")
    
    tester = QdrantFilterTest()
    
    # 初始化
    if not tester.setup():
        print("\n❌ 初始化失败，退出测试")
        return 1
    
    # 添加测试数据
    if not tester.add_test_memories():
        print("\n❌ 添加测试数据失败，退出测试")
        return 1
    
    try:
        # 运行所有测试
        tester.run_all_tests()
        
        # 打印摘要
        tester.print_summary()
        
    finally:
        # 清理
        tester.cleanup()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
