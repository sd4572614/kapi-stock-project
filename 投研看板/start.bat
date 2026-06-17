@echo off
chcp 65001 >nul
title A股投研看板 - 启动

echo ============================================
echo   A股投研看板 - 一键启动
echo ============================================
echo.

set PYTHON=D:\Python\python.exe
set PROJECT_DIR=D:\ai\股票项目\投研看板

echo [1/2] A-Stock-Data 适配器自检...
cd /d "%PROJECT_DIR%"
%PYTHON% a_stock_adapter.py
echo.

echo [2/2] 启动 VIBE-TRADING API 服务器...
echo   看板: http://127.0.0.1:8000
echo   文档: http://127.0.0.1:8000/docs
echo.
cd /d "%PROJECT_DIR%\VIBE-TRADING\agent"
start http://127.0.0.1:8000
%PYTHON% run_server.py

pause
