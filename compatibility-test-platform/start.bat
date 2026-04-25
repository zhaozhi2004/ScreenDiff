@echo off
chcp 65001 >nul 2>&1
title ScreenDiff - 跨浏览器视觉回归测试平台

echo.
echo  ===================================================
echo    ScreenDiff - 跨浏览器视觉回归测试平台
echo  ===================================================
echo.

:: 检查 Python
echo [1/3] 检查 Python...
where python >nul 2>&1
if errorlevel 1 (
    echo       [错误] 未找到 Python，请先安装 Python 3.8+
    echo       下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo       [OK] Python 已安装

:: 检查依赖
echo [2/3] 检查依赖...
python -c "import flask" 2>nul
if errorlevel 1 (
    echo       正在安装依赖...
    pip install -r requirements.txt
    pip install playwright
    python -m playwright install chromium
)
echo       [OK] 依赖已就绪

:: 初始化数据库
echo [3/3] 检查数据库...
if not exist "data\test_platform.db" (
    python init_db.py
)

:: 启动服务
echo.
echo  +-----------------------------------------------------+
echo  ^|  访问地址: http://localhost:5000                    ^
echo  ^|  按 Ctrl+C 停止服务                                ^
echo  +-----------------------------------------------------+
echo.

:: 自动打开浏览器
start "" /b cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:5000"

:: 启动 Flask
python app.py

echo.
echo 服务已停止
pause
