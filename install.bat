@echo off
chcp 65001 >nul
title 日语视频翻译工具 - 安装依赖

echo ============================================
echo    日语视频翻译工具 - 一键安装
echo ============================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10+
    echo 下载地址：https://www.python.org/downloads/
    echo 安装时请勾选 "Add Python to PATH"
    pause
    exit /b 1
)

echo [1/2] 正在安装依赖包，请稍候...
echo.

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo [错误] 依赖安装失败，请检查网络连接
    echo 如使用代理，请先设置代理后重试
    pause
    exit /b 1
)

echo.
echo [2/2] 安装完成！
echo.

:: 可选：安装 NVIDIA CUDA 运行库（有 NVIDIA 显卡可选 Y，可大幅提速）
echo ============================================
echo  [可选] 是否安装 NVIDIA CUDA 加速库？
echo  安装后语音识别会用显卡加速（快很多）
echo  需要下载约 1.1GB，仅需安装一次
echo ============================================
set /p INSTALL_CUDA="输入 Y 安装，直接回车跳过："
if /i "%INSTALL_CUDA%"=="Y" (
    echo.
    echo 正在下载安装 CUDA 运行库，请耐心等待...
    python -m pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
    if errorlevel 1 (
        echo.
        echo [提示] CUDA 库安装失败，可稍后手动执行：
        echo   python -m pip install nvidia-cublas-cu12 nvidia-cudnn-cu12 -i https://pypi.tuna.tsinghua.edu.cn/simple
        echo 没装也不影响使用，程序会自动用 CPU 模式运行。
    ) else (
        echo.
        echo [成功] CUDA 加速库安装完成！设备选「自动」即可用显卡加速。
    )
)

echo.
echo ============================================
echo  安装成功！双击 run.bat 即可启动工具
echo ============================================
echo.
pause
