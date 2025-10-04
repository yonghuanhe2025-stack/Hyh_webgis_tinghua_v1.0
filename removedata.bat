@echo off
setlocal EnableExtensions
REM 只清空 test_data 内的所有文件与子文件夹，不删除 test_data 目录本身
REM 双击直接运行，无需确认

REM 切换到脚本所在目录
cd /d "%~dp0"

set "TARGET=test_data"

REM 若目录不存在则创建为空目录后退出
if not exist "%TARGET%" (
    md "%TARGET%" 2>nul
    goto :END
)

REM 解除可能阻碍删除的属性
attrib -r -h -s "%TARGET%\*" /S /D 2>nul

REM 删除所有文件
del /q /f /s "%TARGET%\*.*" 2>nul

REM 删除所有子目录
for /d %%D in ("%TARGET%\*") do rd /s /q "%%~fD" 2>nul

:END
endlocal
