param(
    [string]$Url = "http://localhost:5173",
    [switch]$Incognito
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ProfileDir = Join-Path $ProjectRoot ".dev-browser-profile"

if (-not (Test-Path $ProfileDir)) {
    New-Item -ItemType Directory -Path $ProfileDir | Out-Null
}

$edgeCandidates = @(
    "$Env:ProgramFiles(x86)\Microsoft\Edge\Application\msedge.exe",
    "$Env:ProgramFiles\Microsoft\Edge\Application\msedge.exe"
)

$edgePath = $edgeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $edgePath) {
    throw "未找到 Microsoft Edge，请先安装 Edge 或修改脚本中的浏览器路径。"
}

$arguments = @(
    "--user-data-dir=$ProfileDir",
    "--new-window",
    "--no-first-run",
    "--no-default-browser-check"
)

if ($Incognito) {
    $arguments += "--inprivate"
}

$arguments += $Url

Start-Process -FilePath $edgePath -ArgumentList $arguments

Write-Host "已使用独立浏览器环境启动: $Url"
Write-Host "配置目录: $ProfileDir"
