#!/usr/bin/env python3
"""诊断 API 连接问题的脚本。

这个脚本会检查：
1. LLM API 端点的可访问性
2. Embedding API 端点的可访问性
3. API 密钥的有效性
4. 网络连接状况
"""

import asyncio
import httpx
import json
import sys
from pathlib import Path
from dotenv import load_dotenv
import os

# 加载 .env 配置
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

def get_env(key: str, default=None):
    """Get environment variable."""
    return os.getenv(key, default)


async def test_api_connection(base_url: str, api_key: str, provider: str):
    """Test API connection with a simple request."""
    print(f"\n{'='*60}")
    print(f"测试 {provider} API 连接")
    print(f"{'='*60}")
    print(f"端点: {base_url}")
    print(f"密钥: {api_key[:10]}...") if api_key else print("密钥: 未配置")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 尝试一个简单的请求
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            
            if "openai" in base_url.lower() or "vectorengine" in base_url.lower() or "legoutech" in base_url.lower():
                # OpenAI 兼容 API
                print("\n💭 尝试调用 OpenAI 兼容 API...")
                model = get_env("LLM_MODEL", "gpt-4o-mini")
                print(f"   使用模型: {model}")
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": "测试"}],
                    "max_tokens": 10,
                }
                
                try:
                    print(f"   发送请求到: {base_url}/chat/completions")
                    response = await client.post(
                        f"{base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=15.0,
                    )
                    
                    print(f"   状态码: {response.status_code}")
                    
                    if response.status_code == 200:
                        print("   ✅ API 连接成功！")
                        data = response.json()
                        print(f"   响应: {json.dumps(data, ensure_ascii=False)[:150]}...")
                        return True
                    elif response.status_code == 401:
                        print("   ❌ 认证失败 (401)")
                        print("   💡 请检查 API_KEY 是否正确")
                        print(f"   响应: {response.text[:300]}")
                        return False
                    elif response.status_code == 403:
                        print("   ❌ 无权限 (403)")
                        print("   💡 API_KEY 可能没有权限访问此模型")
                        print(f"   响应: {response.text[:300]}")
                        return False
                    elif response.status_code == 404:
                        print("   ❌ 模型未找到 (404)")
                        print(f"   💡 模型 '{model}' 在此 API 上不可用")
                        print(f"   响应: {response.text[:300]}")
                        return False
                    elif response.status_code == 429:
                        print("   ⚠️ 速率限制 (429)")
                        print("   💡 API 调用频率过高，请稍后重试")
                        return False
                    elif response.status_code >= 500:
                        print(f"   ⚠️ 服务器错误 ({response.status_code})")
                        print("   💡 API 服务可能暂时不可用")
                        print(f"   响应: {response.text[:300]}")
                        return False
                    else:
                        print(f"   ⚠️ 未预期的状态码: {response.status_code}")
                        print(f"   响应: {response.text[:300]}")
                        return False
                        
                except httpx.TimeoutException:
                    print(f"   ❌ 请求超时")
                    print("   💡 API 响应太慢，可能是网络问题或服务器过载")
                    return False
                except httpx.RequestError as e:
                    print(f"   ❌ 请求失败: {type(e).__name__}: {e}")
                    print("   💡 可能的原因:")
                    print("      - 网络连接问题")
                    print("      - DNS 解析失败")
                    print("      - 防火墙/代理问题")
                    return False
                    
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        return False


async def test_embedding_api():
    """Test Embedding API connection."""
    embedding_base_url = get_env("EMBEDDING_BASE_URL") or get_env("LLM_BASE_URL")
    embedding_api_key = get_env("EMBEDDING_API_KEY") or get_env("LLM_API_KEY")
    embedding_model = get_env("EMBEDDING_MODEL", "text-embedding-3-small")
    embedding_provider = get_env("EMBEDDING_PROVIDER", "openai")
    
    print(f"\n{'='*60}")
    print(f"测试 {embedding_provider} Embedding API 连接")
    print(f"{'='*60}")
    print(f"端点: {embedding_base_url}")
    print(f"模型: {embedding_model}")
    print(f"密钥: {embedding_api_key[:10]}...") if embedding_api_key else print("密钥: 未配置")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {"Authorization": f"Bearer {embedding_api_key}"} if embedding_api_key else {}
            
            print("\n💭 尝试调用 Embedding API...")
            payload = {
                "model": embedding_model,
                "input": "测试文本",
            }
            
            try:
                response = await client.post(
                    f"{embedding_base_url}/embeddings",
                    headers=headers,
                    json=payload,
                )
                
                print(f"   状态码: {response.status_code}")
                
                if response.status_code == 200:
                    print("   ✅ Embedding API 连接成功！")
                    data = response.json()
                    print(f"   响应摘要: 返回 {len(data.get('data', []))} 个 embedding")
                    return True
                elif response.status_code == 401:
                    print("   ❌ 认证失败 (401)")
                    print("   💡 请检查 EMBEDDING_API_KEY 是否正确")
                    return False
                elif response.status_code == 403:
                    print("   ❌ 无权限 (403)")
                    return False
                elif response.status_code == 429:
                    print("   ⚠️ 速率限制 (429)")
                    return False
                elif response.status_code >= 500:
                    print(f"   ⚠️ 服务器错误 ({response.status_code})")
                    return False
                else:
                    print(f"   ⚠️ 未预期的状态码: {response.status_code}")
                    print(f"   响应: {response.text[:200]}")
                    return False
                    
            except httpx.RequestError as e:
                print(f"   ❌ 请求失败: {e}")
                return False
                
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        return False


async def test_network():
    """Test basic network connectivity."""
    print(f"\n{'='*60}")
    print("测试网络连接")
    print(f"{'='*60}")
    
    common_urls = [
        ("Google DNS", "https://8.8.8.8"),
        ("Cloudflare DNS", "https://1.1.1.1"),
        ("Legotech API", "https://chat.legoutech.cn"),
    ]
    
    for name, url in common_urls:
        try:
            async with httpx.AsyncClient(timeout=5.0, verify=False) as client:
                response = await client.head(url)
                print(f"✅ {name}: 可达 ({response.status_code})")
        except Exception as e:
            print(f"❌ {name}: 不可达 ({type(e).__name__})")


async def main():
    """Main diagnostic function."""
    print("\n🔍 开始诊断 API 连接问题...\n")
    
    # 测试网络
    await test_network()
    
    # 测试 LLM API
    llm_provider = get_env("LLM_PROVIDER", "openai")
    llm_base_url = get_env("LLM_BASE_URL")
    llm_api_key = get_env("LLM_API_KEY")
    
    if not llm_base_url:
        print("\n⚠️ 未配置 LLM_BASE_URL")
    else:
        llm_ok = await test_api_connection(llm_base_url, llm_api_key, f"{llm_provider} LLM")
    
    # 测试 Embedding API
    embedding_ok = await test_embedding_api()
    
    # 总结
    print(f"\n{'='*60}")
    print("诊断总结")
    print(f"{'='*60}")
    
    if llm_base_url:
        print(f"LLM API: {'✅ 可用' if llm_ok else '❌ 不可用'}")
    print(f"Embedding API: {'✅ 可用' if embedding_ok else '❌ 不可用'}")
    
    if not llm_ok or not embedding_ok:
        print("\n💡 建议的解决步骤:")
        print("1. 检查网络连接是否正常")
        print("2. 验证 API 端点 URL 是否正确")
        print("3. 确认 API 密钥是否有效")
        print("4. 检查 API 服务是否在线")
        print("5. 尝试使用本地 Ollama 替代远程 API:")
        print("   - 安装 Ollama: https://ollama.ai")
        print("   - 运行 ollama pull llama2")
        print("   - 设置 LLM_PROVIDER=ollama, LLM_BASE_URL=http://localhost:11434")
    
    sys.exit(0 if (llm_ok and embedding_ok) else 1)


if __name__ == "__main__":
    asyncio.run(main())
