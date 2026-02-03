#!/bin/bash
# MCP AI Memory 快速启动脚本

set -e

echo "🚀 MCP AI Memory 快速启动脚本"
echo "================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker 未安装${NC}"
    echo "请访问 https://www.docker.com/products/docker-desktop 安装 Docker"
    exit 1
fi

echo -e "${GREEN}✅ Docker 已安装${NC}"

# 检查 Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose 未安装${NC}"
    echo "请访问 https://docs.docker.com/compose/install 安装 Docker Compose"
    exit 1
fi

echo -e "${GREEN}✅ Docker Compose 已安装${NC}"
echo ""

# 菜单
echo "请选择启动方案："
echo "1) 仅启动 Qdrant 服务（推荐测试环境）"
echo "2) 启动完整的 Docker Compose（Qdrant + MCP 服务）"
echo "3) 显示帮助信息"
echo "4) 停止所有服务"
echo ""
read -p "请输入选项 (1-4): " choice

case $choice in
    1)
        echo ""
        echo -e "${YELLOW}📦 启动 Qdrant 服务...${NC}"
        docker-compose up -d qdrant
        
        echo ""
        echo -e "${GREEN}✅ Qdrant 服务已启动${NC}"
        echo ""
        echo "🌐 Qdrant 管理界面: http://localhost:6333/dashboard"
        echo ""
        echo "配置 .env 文件："
        cat << 'EOF'
VECTOR_STORE_PROVIDER=qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=mem0_memories
EOF
        echo ""
        echo "然后运行 MCP 服务："
        echo "  TRANSPORT=sse uv run python -m mcp_ai_memory.server"
        ;;
        
    2)
        echo ""
        echo -e "${YELLOW}📦 启动完整 Docker Compose...${NC}"
        
        # 检查 .env 文件
        if [ ! -f .env ]; then
            echo -e "${YELLOW}⚠️  .env 文件不存在，使用示例配置${NC}"
            cp .env.example .env
            echo -e "${YELLOW}📝 请编辑 .env 文件配置 LLM API${NC}"
            echo ""
        fi
        
        docker-compose -f docker-compose.full.yml up -d
        
        echo ""
        echo -e "${GREEN}✅ 所有服务已启动${NC}"
        echo ""
        echo "📊 服务地址："
        echo "  Qdrant: http://localhost:6333"
        echo "  MCP 服务: http://localhost:8050"
        echo ""
        echo "📖 查看日志："
        echo "  docker-compose -f docker-compose.full.yml logs -f"
        echo ""
        echo "⏹️  停止服务："
        echo "  docker-compose -f docker-compose.full.yml down"
        ;;
        
    3)
        echo ""
        echo "📖 快速启动指南"
        echo "===================="
        echo ""
        echo "方案 1: 仅 Qdrant（推荐测试）"
        echo "  $0 选择 1"
        echo "  然后本地启动 MCP 服务"
        echo ""
        echo "方案 2: 完整 Docker Compose（推荐生产）"
        echo "  $0 选择 2"
        echo "  自动启动 Qdrant 和 MCP 服务"
        echo ""
        echo "方案 3: 本地开发（仅开发）"
        echo "  TRANSPORT=sse uv run python -m mcp_ai_memory.server"
        echo ""
        echo "📚 详细文档："
        echo "  cat DEPLOYMENT.md"
        echo ""
        echo "🔧 诊断工具："
        echo "  uv run python diagnose_api.py"
        echo ""
        echo "🧪 运行测试："
        echo "  uv run python test_mcp_server.py"
        ;;
        
    4)
        echo ""
        echo -e "${YELLOW}⏹️  停止所有服务...${NC}"
        
        # 停止本地进程
        if pgrep -f "mcp_ai_memory" > /dev/null; then
            echo -e "${YELLOW}停止本地 MCP 服务...${NC}"
            pkill -f "mcp_ai_memory" || true
        fi
        
        # 停止 Docker 容器
        if docker ps | grep -q "qdrant\|mcp-ai-memory"; then
            echo -e "${YELLOW}停止 Docker 容器...${NC}"
            docker-compose down || docker-compose -f docker-compose.full.yml down || true
        fi
        
        echo ""
        echo -e "${GREEN}✅ 所有服务已停止${NC}"
        ;;
        
    *)
        echo -e "${RED}❌ 无效选项${NC}"
        exit 1
        ;;
esac

echo ""
