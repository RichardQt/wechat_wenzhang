@echo off
chcp 65001 >nul
echo ========================================
echo      微信公众号爬虫 - 24小时自动运行
echo ========================================
echo.
echo 正在启动爬虫，每24小时自动执行一次...
echo 按 Ctrl+C 可以停止程序
echo.
.\venv\Scripts\python.exe start.py
pause