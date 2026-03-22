#!/usr/bin/env pwsh
# 启动 FastAPI 后端开发服务器

Push-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)

# 设置 PYTHONPATH
$env:PYTHONPATH = "$PWD\backend"

# 进入 backend 目录
cd backend

# 检查依赖
Write-Host "📦 检查依赖..." -ForegroundColor Green
if (-not (Test-Path ".\requirements.txt")) {
    Write-Host "❌ 找不到 requirements.txt" -ForegroundColor Red
    exit 1
}

# 启动服务
Write-Host "🚀 启动 FastAPI 服务..." -ForegroundColor Green
Write-Host "📍 Swagger UI: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "📍 ReDoc: http://localhost:8000/redoc" -ForegroundColor Cyan
Write-Host "`n" -ForegroundColor Gray

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Pop-Location
