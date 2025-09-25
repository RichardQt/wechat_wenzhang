@echo off
chcp 65001 >nul
echo ========================================
echo    微信公众号爬虫 - 定时任务启动器
echo ========================================
echo.
echo 程序将在明天凌晨 00:01 自动执行一次爬虫任务
echo 按 Ctrl+C 可以随时停止程序
echo.
echo 正在启动定时任务...
echo.
.\venv\Scripts\python.exe scheduled_task.py
echo.
echo 定时任务已完成
pause