param(
    [string]$Host = "127.0.0.1",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$targets = Get-CimInstance Win32_Process | Where-Object {
    ($_.Name -ieq "python.exe" -or $_.Name -ieq "conda.exe") -and
    $_.CommandLine -and (
        $_.CommandLine -match "uvicorn\s+app\.main:app" -or
        $_.CommandLine -match "python\s+-m\s+uvicorn\s+app\.main:app"
    )
}

if (-not $targets) {
    Write-Host "未找到 office-agent demo 服务进程（uvicorn app.main:app）。" -ForegroundColor Yellow
    exit 0
}

$stopped = 0
foreach ($proc in $targets) {
    try {
        Stop-Process -Id $proc.ProcessId -Force
        $stopped++
    }
    catch {
        Write-Host "停止进程失败 PID=$($proc.ProcessId): $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "已停止 $stopped 个 demo 服务进程。" -ForegroundColor Green
Write-Host "如需清理隔离浏览器数据，可删除 .isolated/browser-profile 目录。" -ForegroundColor Cyan
