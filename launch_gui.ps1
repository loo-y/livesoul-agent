$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    Write-Host "LiveSoul: 未找到 .venv\Scripts\python.exe" -ForegroundColor Yellow
    Write-Host "LiveSoul: 请先在项目根目录创建并安装虚拟环境。" -ForegroundColor Yellow
    Read-Host "按回车键退出"
    exit 1
}

Start-Process -FilePath $python -WorkingDirectory $PSScriptRoot -ArgumentList "-m", "src.gui_app"
