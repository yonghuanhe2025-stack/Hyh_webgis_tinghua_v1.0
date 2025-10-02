@echo off
REM 安装 Conda 环境
echo Installing Conda environment from gis_env_environment.yml...
conda env create -f gis_env_environment.yml
echo Conda environment "gis_env" has been installed successfully.
pause
