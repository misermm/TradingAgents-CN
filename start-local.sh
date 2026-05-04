#!/usr/bin/env bash
set -e

echo "========================================"
echo "  TradingAgents-CN 本地开发一键启动"
echo "========================================"
echo ""

echo "[1/5] 检查 Docker..."
if ! command -v docker &> /dev/null; then
    echo "   ❌ Docker 未安装，请先安装 Docker"
    exit 1
fi
if ! docker compose version &> /dev/null; then
    echo "   ❌ Docker Compose 不可用，请升级 Docker"
    exit 1
fi
echo "   ✅ Docker 可用"

echo ""
echo "[2/5] 检查环境配置..."
if [ ! -f ".env.local" ]; then
    echo "   ⚠️  .env.local 不存在，正在从 .env.docker 创建..."
    if [ -f ".env.docker" ]; then
        cp .env.docker .env.local
        echo "   ✅ 已创建 .env.local（请编辑填入真实 API 密钥）"
    else
        echo "   ❌ .env.docker 也不存在，请手动创建 .env.local"
        exit 1
    fi
else
    echo "   ✅ .env.local 已存在"
fi

echo ""
echo "[3/5] 创建必要目录..."
mkdir -p logs data
echo "   ✅ 目录就绪"

echo ""
echo "[4/5] 清理旧容器..."
docker compose -f docker-compose.local.yml down --remove-orphans 2>/dev/null || true
echo "   ✅ 清理完成"

echo ""
echo "[5/5] 启动所有服务..."
echo "   📦 启动中（首次启动需安装依赖，约需 3-5 分钟）..."
echo ""

docker compose -f docker-compose.local.yml up -d

echo ""
echo "========================================"
echo "  🎉 服务启动成功！"
echo "========================================"
echo ""
echo "  📍 访问地址:"
echo "     前端 (Vite 开发服务器):  http://localhost:5173"
echo "     后端 API:                http://localhost:8000"
echo "     API 文档:                http://localhost:8000/docs"
echo "     MongoDB:                 localhost:27017"
echo "     Redis:                   localhost:6379"
echo ""
echo "  💡 开发提示:"
echo "     - 修改后端代码后自动热重载 (uvicorn --reload)"
echo "     - 修改前端代码后自动热更新 (Vite HMR)"
echo "     - 查看 backend 日志:  docker compose -f docker-compose.local.yml logs -f backend"
echo "     - 查看 frontend 日志: docker compose -f docker-compose.local.yml logs -f frontend"
echo "     - 停止所有服务:      docker compose -f docker-compose.local.yml down"
echo ""

sleep 10

echo "📊 当前服务状态:"
docker compose -f docker-compose.local.yml ps
