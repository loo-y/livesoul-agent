@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [LiveSoul] 未找到 .venv\Scripts\python.exe
  echo [LiveSoul] 请先在项目根目录创建并安装虚拟环境。
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ".\.venv\Scripts\Activate.ps1; python -m src.gui_app"

if errorlevel 1 (
  echo.
  echo [LiveSoul] GUI 启动失败，请检查依赖或查看终端报错。
  pause
)

endlocal
