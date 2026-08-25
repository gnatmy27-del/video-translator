@echo off
chcp 65001 >nul
title 视频翻译工具

cd /d "%~dp0"

:: 如果安装了 pip 的 CUDA 运行库（nvidia-cublas/cudnn），把 DLL 目录加入 PATH
set "PYDIR=%LOCALAPPDATA%\Programs\Python\Python312\Lib\site-packages\nvidia"
if exist "%PYDIR%\cublas\bin" set "PATH=%PYDIR%\cublas\bin;%PATH%"
if exist "%PYDIR%\cudnn\bin"  set "PATH=%PYDIR%\cudnn\bin;%PATH%"

:: 用 pythonw 启动，不显示黑色终端窗口（界面自带运行日志）
where pythonw.exe >nul 2>nul
if not errorlevel 1 (
    start "" pythonw.exe main.py
) else (
    start "" python main.py
)

