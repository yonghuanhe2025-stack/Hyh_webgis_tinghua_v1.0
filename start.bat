@echo off
REM 激活 conda 环境
call conda activate gis_env

REM 运行 Python 脚本
python main.py

REM 保持窗口打开，查看输出
pause
