<#
.SYNOPSIS
    TradingAgents-CN 一键重新部署脚本 (Windows PowerShell)
.DESCRIPTION
    停止旧容器 -> 重新构建镜像 -> 清理悬空镜像 -> 启动服务 -> 健康检查
.USAGE
    powershell -ExecutionPolicy Bypass -File scripts\redeploy.ps1
    powershell -ExecutionPolicy Bypass -File scripts\redeploy.ps1 -SkipBuild
    powershell -ExecutionPolicy Bypass -File scripts\redeploy.ps1 -Services backend,worker
#>

param(
    [switch]$SkipBuild,
    [switch]$SkipFrontend,
    [string[]]$Services,
    [int]$HealthCheckTimeout = 120
)

$ErrorActionPreference = "Continue"

function Write-Step($step, $text) {
    Write-Host ""
    Write-Host "[$step] $text" -ForegroundColor Cyan
    Write-Host ("-" * 50) -ForegroundColor DarkGray
}

function Write-Ok($text) {
    Write-Host "  OK $text" -ForegroundColor Green
}

function Write-Warn($text) {
    Write-Host "  WARN $text" -ForegroundColor Yellow
}

function Write-Fail($text) {
    Write-Host "  FAIL $text" -ForegroundColor Red
}

function Test-HttpEndpoint($url, $maxRetries, $intervalSec) {
    for ($i = 1; $i -le $maxRetries; $i++) {
        try {
            $r = Invoke-WebRequest -Uri $url -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
            if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 400) {
                return $true
            }
        } catch {}
        if ($i -lt $maxRetries) {
            Start-Sleep -Seconds $intervalSec
        }
    }
    return $false
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " TradingAgents-CN  一键重新部署" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SkipBuild    = $SkipBuild" -ForegroundColor DarkGray
Write-Host "  SkipFrontend = $SkipFrontend" -ForegroundColor DarkGray
Write-Host "  Services     = $(if ($Services) { $Services -join ',' } else { 'all' })" -ForegroundColor DarkGray
Write-Host ""

# ---------- Step 1: Stop ----------
Write-Step "1/6" "Stopping existing containers"
docker compose down --remove-orphans 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Ok "Containers stopped"
} else {
    Write-Warn "Stop had warnings (may be normal if containers weren't running)"
}

# ---------- Step 2: Build ----------
if (-not $SkipBuild) {
    Write-Step "2/6" "Building Docker images"
    
    $buildCmd = "docker compose build"
    if ($Services) {
        $buildCmd += " " + ($Services -join " ")
    } elseif ($SkipFrontend) {
        $buildCmd += " backend worker"
    }
    
    Write-Host "  > $buildCmd" -ForegroundColor DarkGray
    Invoke-Expression $buildCmd
    
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "Images built successfully"
    } else {
        Write-Fail "Image build failed"
        exit 1
    }

    # Prune dangling images
    Write-Host "  Cleaning dangling images..." -ForegroundColor DarkGray
    docker image prune -f 2>$null | Out-Null
    Write-Ok "Dangling images cleaned"
} else {
    Write-Step "2/6" "Build skipped (-SkipBuild)"
}

# ---------- Step 3: Start ----------
Write-Step "3/6" "Starting containers"
$upCmd = "docker compose up -d"
if ($Services) {
    $upCmd += " " + ($Services -join " ")
} elseif ($SkipFrontend) {
    $upCmd += " backend worker mongodb redis"
}

Write-Host "  > $upCmd" -ForegroundColor DarkGray
Invoke-Expression $upCmd

if ($LASTEXITCODE -eq 0) {
    Write-Ok "Containers started"
} else {
    Write-Fail "Container start failed"
    exit 1
}

# ---------- Step 4: Wait for healthy ----------
Write-Step "4/6" "Waiting for services to be healthy (timeout: ${HealthCheckTimeout}s)"

$elapsed = 0
$interval = 5
$allHealthy = $false

while ($elapsed -lt $HealthCheckTimeout) {
    $psOutput = docker compose ps --format "json" 2>$null
    $statuses = @()
    
    try {
        $lines = $psOutput -split "`n" | Where-Object { $_.Trim() -ne "" }
        foreach ($line in $lines) {
            $obj = $line | ConvertFrom-Json -ErrorAction SilentlyContinue
            if ($obj) {
                $statuses += [PSCustomObject]@{
                    Name   = $obj.Name
                    Health = $obj.Health
                    State  = $obj.State
                }
            }
        }
    } catch {
        $statuses = @()
    }

    $running = ($statuses | Where-Object { $_.State -eq "running" }).Count
    $healthy = ($statuses | Where-Object { $_.Health -eq "healthy" -or $_.State -eq "running" }).Count
    $total = ($statuses).Count

    Write-Host "  [$elapsed/${HealthCheckTimeout}s] running=$running healthy=$healthy total=$total" -ForegroundColor DarkGray

    if ($total -gt 0 -and $healthy -ge $total) {
        $allHealthy = $true
        break
    }

    Start-Sleep -Seconds $interval
    $elapsed += $interval
}

if ($allHealthy) {
    Write-Ok "All services healthy"
} else {
    Write-Warn "Not all services reached healthy state within timeout"
}

# ---------- Step 5: Health check ----------
Write-Step "5/6" "Running health checks"

# Backend API
$backendOk = Test-HttpEndpoint "http://localhost:8000/health" 10 3
if ($backendOk) {
    Write-Ok "Backend API  http://localhost:8000"
} else {
    Write-Warn "Backend API not responding (may still be starting)"
}

# Frontend
$frontendOk = Test-HttpEndpoint "http://localhost:80" 5 3
if ($frontendOk) {
    Write-Ok "Frontend     http://localhost:80"
} else {
    Write-Warn "Frontend not responding (may still be starting)"
}

# Login test
Write-Host "  Testing login..." -ForegroundColor DarkGray
try {
    $loginBody = @{ username = "admin"; password = "admin123" } | ConvertTo-Json
    $loginResp = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/login" -Method Post -Body $loginBody -ContentType "application/json" -TimeoutSec 10 -ErrorAction Stop
    if ($loginResp.success) {
        Write-Ok "Login test passed (admin/admin123)"
    } else {
        Write-Warn "Login returned but not successful"
    }
} catch {
    Write-Warn "Login test failed: $($_.Exception.Message)"
}

# ---------- Step 6: Summary ----------
Write-Step "6/6" "Deployment summary"

docker compose ps --format "table {{.Name}}\t{{.State}}\t{{.Health}}\t{{.Ports}}" 2>$null

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($backendOk) {
    Write-Host " Deployment completed!" -ForegroundColor Green
} else {
    Write-Host " Deployment finished (with warnings)" -ForegroundColor Yellow
}
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Frontend : http://localhost:80" -ForegroundColor White
Write-Host "  Backend  : http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs : http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Login    : admin / admin123" -ForegroundColor White
Write-Host ""
Write-Host "  Useful commands:" -ForegroundColor DarkGray
Write-Host "    View logs : docker compose logs -f backend" -ForegroundColor DarkGray
Write-Host "    Restart   : docker compose restart backend worker" -ForegroundColor DarkGray
Write-Host "    Stop all  : docker compose down" -ForegroundColor DarkGray
Write-Host ""
