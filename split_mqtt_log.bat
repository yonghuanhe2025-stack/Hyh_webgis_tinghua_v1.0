@echo off
setlocal enabledelayedexpansion

REM 输入文件
set INPUT=log/mqtt_log_20250914_182958.txt
REM 输出目录
set OUTDIR=test_data

REM 创建输出目录（如果不存在）
if not exist "%OUTDIR%" mkdir "%OUTDIR%"

for /f "usebackq delims=" %%a in ("%INPUT%") do (
    set "line=%%a"

    REM 提取时间戳 [2025-09-01 21:35:16]
    for /f "tokens=1,2 delims=[]" %%i in ("%%a") do (
        set "timestamp=%%i"
    )

    REM 清理非法字符（转成文件名）
    set "timestamp=!timestamp: =_!"
    set "timestamp=!timestamp:-=_!"
    set "timestamp=!timestamp::=_!"

    REM 打印到终端
    echo !line!

    REM 保存文件
    echo %%a > "%OUTDIR%\!timestamp!.txt"

    REM 延时 0.2 秒
    ping -n 1 -w 200 127.0.0.1 >nul
)

echo 完成！文件已保存到 %OUTDIR%
pause
