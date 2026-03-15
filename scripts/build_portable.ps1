$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoRoot

$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "未找到 .venv\Scripts\python.exe，请先创建虚拟环境并安装依赖。"
}

$buildRoot = Join-Path $repoRoot "build\portable"
$distRoot = Join-Path $repoRoot "dist"
$guiDist = Join-Path $buildRoot "gui"
$runtimeDist = Join-Path $buildRoot "runtime"
$workRoot = Join-Path $buildRoot "work"
$finalBundle = Join-Path $distRoot "LiveSoul_Portable"
$systemFfplay = "C:\Program Files\ffmpeg\bin\ffplay.exe"

Remove-Item $buildRoot -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $finalBundle -Recurse -Force -ErrorAction SilentlyContinue

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onedir `
    --name LiveSoulGUI `
    --paths $repoRoot `
    --distpath $guiDist `
    --workpath (Join-Path $workRoot "gui") `
    packaging\gui_entry.py

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --console `
    --onefile `
    --name LiveSoulRuntime `
    --paths $repoRoot `
    --distpath $runtimeDist `
    --workpath (Join-Path $workRoot "runtime") `
    packaging\runtime_entry.py

New-Item -ItemType Directory -Path $finalBundle -Force | Out-Null

Copy-Item (Join-Path $guiDist "LiveSoulGUI\*") $finalBundle -Recurse -Force
Copy-Item (Join-Path $runtimeDist "LiveSoulRuntime.exe") $finalBundle -Force
Copy-Item "default_config.json" $finalBundle -Force
Copy-Item "profiles" (Join-Path $finalBundle "profiles") -Recurse -Force

$runtimeDir = Join-Path $finalBundle "runtime"
New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $runtimeDir "audio") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $runtimeDir "frames") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $runtimeDir "memory") -Force | Out-Null

if (Test-Path -LiteralPath $systemFfplay) {
    $ffmpegBin = Join-Path $finalBundle "tools\ffmpeg\bin"
    New-Item -ItemType Directory -Path $ffmpegBin -Force | Out-Null
    Copy-Item $systemFfplay (Join-Path $ffmpegBin "ffplay.exe") -Force
}

$startCmd = @"
@echo off
cd /d "%~dp0"
start "" "LiveSoulGUI.exe"
"@
$startCmdContent = $startCmd -replace "`r?`n", "`r`n"
[System.IO.File]::WriteAllText((Join-Path $finalBundle "Start-LiveSoul.cmd"), $startCmdContent, (New-Object System.Text.UTF8Encoding($false)))

Write-Host ""
Write-Host "绿色包已生成：" -ForegroundColor Green
Write-Host $finalBundle -ForegroundColor Cyan
