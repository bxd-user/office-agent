param(
    [string]$EnvName = "agent",
    [string]$Host = "127.0.0.1",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$IsolatedRoot = Join-Path $ProjectRoot ".isolated"
$BrowserProfileDir = Join-Path $IsolatedRoot "browser-profile"

New-Item -ItemType Directory -Force -Path $IsolatedRoot | Out-Null
New-Item -ItemType Directory -Force -Path $BrowserProfileDir | Out-Null

$CondaExe = "C:/Users/20557/miniconda3/Scripts/conda.exe"
if (-not (Test-Path $CondaExe)) {
    throw "未找到 conda 可执行文件: $CondaExe"
}

$ServerCommand = "Set-Location '$ProjectRoot'; & '$CondaExe' run -n $EnvName python -m uvicorn app.main:app --host $Host --port $Port --reload"
Start-Process -FilePath "powershell" -ArgumentList @("-NoExit", "-Command", $ServerCommand) | Out-Null

$HealthUrl = "http://$Host`:$Port/"
$ServerReady = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 1 | Out-Null
        $ServerReady = $true
        break
    }
    catch {
        Start-Sleep -Seconds 1
    }
}

if (-not $ServerReady) {
    throw "服务启动超时，请检查新开的服务窗口日志。"
}

function Start-IsolatedBrowser {
    param(
        [string]$Url,
        [string]$ProfilePath
    )

    $EdgePath = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
    $ChromePath = "C:/Program Files/Google/Chrome/Application/chrome.exe"
    $FirefoxPath = "C:/Program Files/Mozilla Firefox/firefox.exe"

    if (Test-Path $EdgePath) {
        Start-Process -FilePath $EdgePath -ArgumentList @("--user-data-dir=$ProfilePath", "--new-window", $Url) | Out-Null
        return
    }

    if (Test-Path $ChromePath) {
        Start-Process -FilePath $ChromePath -ArgumentList @("--user-data-dir=$ProfilePath", "--new-window", $Url) | Out-Null
        return
    }

    if (Test-Path $FirefoxPath) {
        $FirefoxProfile = Join-Path $ProfilePath "firefox-profile"
        New-Item -ItemType Directory -Force -Path $FirefoxProfile | Out-Null
        Start-Process -FilePath $FirefoxPath -ArgumentList @("-no-remote", "-profile", $FirefoxProfile, $Url) | Out-Null
        return
    }

    throw "未检测到 Edge/Chrome/Firefox，无法保证浏览器隔离启动。"
}

Start-IsolatedBrowser -Url $HealthUrl -ProfilePath $BrowserProfileDir
Write-Host "已启动服务并打开隔离浏览器: $HealthUrl" -ForegroundColor Green
