@echo off
REM 导出 conda 环境为一个 YAML 文件
call conda activate gis_env
conda env export > gis_env_environment.yml
echo Conda environment "gis_env" has been exported to gis_env_environment.yml
pause
