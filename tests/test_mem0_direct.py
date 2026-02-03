#!/usr/bin/env python3
"""直接测试 Mem0 库与 API 的连接。"""

import os
import sys
import traceback
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_ai_memory.config import create_mem0_client, DEFAULT_USER_ID


def test_mem0_direct():
    """直接测试 Mem0 连接。"""
    print("\n" + "="*60)
    print("直接测试 Mem0 库连接")
    print("="*60)
    
    print("\n配置信息:")
    print(f"  LLM 提供商: {os.getenv('LLM_PROVIDER', 'openai')}")
    print(f"  LLM 基础 URL: {os.getenv('LLM_BASE_URL')}")
    print(f"  LLM 模型: {os.getenv('LLM_MODEL')}")
    print(f"  Embedding 提供商: {os.getenv('EMBEDDING_PROVIDER', 'openai')}")
    print(f"  默认用户 ID: {DEFAULT_USER_ID}")
    
    try:
        print("\n1️⃣ 创建 Mem0 客户端...")
        client = create_mem0_client()
        print("   ✅ Mem0 客户端创建成功")
        
        print("\n2️⃣ 测试添加记忆...")
        test_text = "我是 Python 开发者，喜欢使用 FastAPI。"
        print(f"   输入文本: {test_text}")
        
        try:
            result = client.add(
                messages=[{"role": "user", "content": test_text}],
                user_id=f"test_direct_{os.getpid()}",
            )
            print("   ✅ 记忆添加成功！")
            print(f"   结果: {result}")
            
        except Exception as e:
            print(f"   ❌ 记忆添加失败: {type(e).__name__}")
            print(f"   错误: {str(e)}")
            print(f"\n   完整错误追踪:")
            traceback.print_exc()
            
            # 尝试提取更多信息
            if hasattr(e, '__cause__'):
                print(f"\n   原因错误: {e.__cause__}")
            if hasattr(e, 'response'):
                print(f"   响应状态: {getattr(e, 'status_code', 'N/A')}")
                print(f"   响应内容: {getattr(e, 'text', 'N/A')}")
        
    except Exception as e:
        print(f"   ❌ 初始化失败: {type(e).__name__}: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    test_mem0_direct()
