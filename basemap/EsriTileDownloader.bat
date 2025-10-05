@echo off
setlocal EnableExtensions
chcp 65001 >nul

REM 双击运行 PowerShell 脚本（需与本 bat 放同一目录）
set "PS1=%~dp0EsriTileDownloader.ps1"

if not exist "%PS1%" (
  echo [ERROR] 找不到 PowerShell 脚本：%PS1%
  echo 请先将 EsriTileDownloader.ps1 放在此文件夹。
  echo.
  pause
  exit /b 1
)

where powershell >nul 2>nul
if errorlevel 1 (
  echo [ERROR] 未检测到 PowerShell。请在 Windows 中启用或安装 PowerShell。
  echo.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
echo.
echo 任务结束。按任意键关闭...
pause >nul
endlocal
