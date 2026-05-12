@echo off
setlocal enabledelayedexpansion

set "MODE=dev"
set "SKIP_BUILD=0"
set "HEALTH_TIMEOUT=120"

:parse_args
if "%~1"=="" goto :done_args
if /i "%~1"=="--prod" set "MODE=prod"
if /i "%~1"=="--dev" set "MODE=dev"
if /i "%~1"=="--skip-build" set "SKIP_BUILD=1"
if /i "%~1"=="--timeout" (
    set "HEALTH_TIMEOUT=%~2"
    shift
)
if /i "%~1"=="--help" goto :show_help
shift
goto :parse_args
:done_args

if "%MODE%"=="dev" (
    set "COMPOSE_FILE=docker-compose.local.yml"
    set "TOTAL_SERVICES=5"
) else (
    set "COMPOSE_FILE=docker-compose.yml"
    set "TOTAL_SERVICES=7"
)

echo.
echo ========================================
echo  TradingAgents-CN  Redeploy
echo ========================================
echo  Mode        = %MODE% (%COMPOSE_FILE%)
echo  SkipBuild   = %SKIP_BUILD%
echo  Timeout     = %HEALTH_TIMEOUT%s
echo.

echo [1/6] Stopping existing containers
echo --------------------------------------------------
docker compose -f %COMPOSE_FILE% down --remove-orphans
echo.

if "%SKIP_BUILD%"=="1" (
    echo [2/6] Build skipped
    echo.
    goto :step3
)

echo [2/6] Building Docker images
echo --------------------------------------------------
docker compose -f %COMPOSE_FILE% build
if errorlevel 1 (
    echo [FAIL] Image build failed
    exit /b 1
)
echo Cleaning dangling images...
docker image prune -f
echo.

:step3
echo [3/6] Starting containers
echo --------------------------------------------------
docker compose -f %COMPOSE_FILE% up -d
if errorlevel 1 (
    echo [FAIL] Container start failed
    exit /b 1
)
echo.

echo [4/6] Waiting for services ^(timeout: %HEALTH_TIMEOUT%s^)
echo --------------------------------------------------
set /a "ELAPSED=0"
set /a "INTERVAL=5"
set "ALL_UP=0"

:wait_loop
if !ELAPSED! geq %HEALTH_TIMEOUT% goto :wait_done

set "RUNNING_COUNT=0"
for /f %%c in ('docker compose -f %COMPOSE_FILE% ps --format "{{.State}}" 2^>nul ^| find /c "running"') do set "RUNNING_COUNT=%%c"

echo   [!ELAPSED!/%HEALTH_TIMEOUT%s] running=!RUNNING_COUNT! / %TOTAL_SERVICES%

if "!RUNNING_COUNT!"=="%TOTAL_SERVICES%" (
    set "ALL_UP=1"
    timeout /t 10 /nobreak >nul 2>&1
    goto :wait_done
)

timeout /t !INTERVAL! /nobreak >nul 2>&1
set /a "ELAPSED+=INTERVAL"
goto :wait_loop

:wait_done
if "!ALL_UP!"=="1" (
    echo   [OK] All %TOTAL_SERVICES% services are running
) else (
    echo   [WARN] Not all services reached running state within timeout
)
echo.

echo [5/6] Running health checks
echo --------------------------------------------------

set "BACKEND_OK=0"
for /l %%r in (1,1,20) do (
    if "!BACKEND_OK!"=="0" (
        curl.exe -sf http://localhost:8000/api/health >nul 2>&1
        if !errorlevel! equ 0 (
            set "BACKEND_OK=1"
        ) else (
            timeout /t 3 /nobreak >nul 2>&1
        )
    )
)
if "!BACKEND_OK!"=="1" (
    echo   [OK] Backend API  http://localhost:8000
    for /f "delims=" %%i in ('curl.exe -sf http://localhost:8000/api/health 2^>nul') do set "HEALTH_INFO=%%i"
    echo !HEALTH_INFO! | findstr /C:"ready" >nul 2>&1
    if !errorlevel! equ 0 (
        echo   [OK] Backend ready, all components healthy
    )
) else (
    echo   [WARN] Backend API not responding
)

if "%MODE%"=="dev" (
    set "FRONTEND_OK=0"
    for /l %%r in (1,1,10) do (
        if "!FRONTEND_OK!"=="0" (
            curl.exe -sf http://localhost:5173 >nul 2>&1
            if !errorlevel! equ 0 (
                set "FRONTEND_OK=1"
            ) else (
                timeout /t 3 /nobreak >nul 2>&1
            )
        )
    )
    if "!FRONTEND_OK!"=="1" (
        echo   [OK] Frontend     http://localhost:5173
    ) else (
        echo   [WARN] Frontend not responding
    )
) else (
    set "NGINX_OK=0"
    for /l %%r in (1,1,10) do (
        if "!NGINX_OK!"=="0" (
            curl.exe -sf http://localhost:80/health >nul 2>&1
            if !errorlevel! equ 0 (
                set "NGINX_OK=1"
            ) else (
                timeout /t 3 /nobreak >nul 2>&1
            )
        )
    )
    if "!NGINX_OK!"=="1" (
        echo   [OK] Nginx+Frontend http://localhost:80
    ) else (
        echo   [WARN] Nginx+Frontend not responding
    )
)

echo   Testing login...
curl.exe -sf -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" -d "{\"username\":\"admin\",\"password\":\"admin123\"}" >nul 2>&1
if !errorlevel! equ 0 (
    echo   [OK] Login test passed
) else (
    echo   [WARN] Login test failed
)
echo.

echo [6/6] Deployment summary
echo --------------------------------------------------
docker compose -f %COMPOSE_FILE% ps
echo.

echo ========================================
if "!BACKEND_OK!"=="1" (
    echo  Deployment completed!
) else (
    echo  Deployment finished ^(with warnings^)
)
echo ========================================
echo.
if "%MODE%"=="dev" (
    echo   Frontend : http://localhost:5173
    echo   Backend  : http://localhost:8000
) else (
    echo   App      : http://localhost:80
    echo   Backend  : http://localhost:8000
)
echo   API Docs : http://localhost:8000/docs
echo   Login    : admin / admin123
echo.
echo   Useful commands:
echo     View logs : docker compose -f %COMPOSE_FILE% logs -f backend
echo     Restart   : docker compose -f %COMPOSE_FILE% restart backend
echo     Stop all  : docker compose -f %COMPOSE_FILE% down
echo.
goto :eof

:show_help
echo.
echo Usage: redeploy.bat [options]
echo.
echo Options:
echo   --dev             Dev mode: docker-compose.local.yml (default)
echo   --prod            Prod mode: docker-compose.yml
echo   --skip-build      Skip docker image build step
echo   --timeout SECS    Health check timeout in seconds (default: 120)
echo   --help            Show this help message
echo.
echo Examples:
echo   redeploy.bat                  Dev mode (build + volume mounts)
echo   redeploy.bat --prod           Prod mode with Dockerfile build
echo   redeploy.bat --skip-build     Skip build step (use cached images)
echo.
goto :eof
