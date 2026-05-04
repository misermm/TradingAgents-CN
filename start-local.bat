@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

echo ========================================
echo   TradingAgents-CN 本地开发一键启动
echo ========================================
echo.

REM 检查 Docker 是否可用
echo [1/5] 检查 Docker...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo    ❌ Docker 未安装或不可用，请先安装 Docker Desktop
    pause
    exit /b 1
)
docker compose version >nul 2>&1
if %errorlevel% neq 0 (
    echo    ❌ Docker Compose 不可用，请升级 Docker Desktop
    pause
    exit /b 1
)
echo    ✅ Docker 可用

REM 检查 .env.local 文件
echo.
echo [2/5] 检查环境配置...
if not exist ".env.local" (
    echo    ⚠️  .env.local 不存在，正在从 .env.docker 创建...
    if exist ".env.docker" (
        copy .env.docker .env.local >nul
        echo    ✅ 已创建 .env.local（请编辑填入真实 API 密钥）
    ) else (
        echo    ❌ .env.docker 也不存在，请手动创建 .env.local
        pause
        exit /b 1
    )
) else (
    echo    ✅ .env.local 已存在
)

REM 创建必要目录
echo.
echo [3/5] 创建必要目录...
if not exist "logs" mkdir logs
if not exist "data" mkdir data
echo    ✅ 目录就绪

REM 停止旧容器
echo.
echo [4/5] 清理旧容器...
docker compose -f docker-compose.local.yml down --remove-orphans 2>nul
echo    ✅ 清理完成

REM 启动服务
echo.
echo [5/5] 启动所有服务...
echo    📦 启动中（首次启动需安装依赖，约需 3-5 分钟）...
echo.

docker compose -f docker-compose.local.yml up -d

if %errorlevel% neq 0 (
    echo.
    echo    ❌ 启动失败，请查看上方错误信息
    echo    💡 常见问题:
    echo       - 端口被占用: 检查 8000/5173/27017/6379 是否被占用
    echo       - .env.local 配置错误: 检查 API 密钥格式
    echo.
    echo    📋 查看详细日志: docker compose -f docker-compose.local.yml logs
    pause
    exit /b 1
)

echo.
echo ========================================
echo   🎉 服务启动成功！
echo ========================================
echo.
echo   📍 访问地址:
echo      前端 (Vite 开发服务器):  http://localhost:5173
echo      后端 API:                http://localhost:8000
echo      API 文档:                http://localhost:8000/docs
echo      MongoDB:                 localhost:27017
echo      Redis:                   localhost:6379
echo.
echo   💡 开发提示:
echo      - 修改后端代码后自动热重载 (uvicorn --reload)
echo      - 修改前端代码后自动热更新 (Vite HMR)
echo      - 查看 backend 日志:  docker compose -f docker-compose.local.yml logs -f backend
echo      - 查看 frontend 日志: docker compose -f docker-compose.local.yml logs -f frontend
echo      - 停止所有服务:      docker compose -f docker-compose.local.yml down
echo      - 重启单个服务:      docker compose -f docker-compose.local.yml restart backend
echo.
echo   ⚠️  首次启动需等待依赖安装完成，backend 健康检查可能需要 2 分钟
echo.

REM 等待并显示服务状态
echo 📋 等待服务就绪...
timeout /t 15 /nobreak >nul

echo.
echo 📊 当前服务状态:
docker compose -f docker-compose.local.yml ps

echo.
pause
