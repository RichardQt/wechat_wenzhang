@echo off
chcp 65001 >nul
echo ========================================
echo    微信公众号爬虫 - 立即执行模式
echo ========================================
echo.
echo 正在立即执行爬虫任务（不等待）...
echo.
.\venv\Scripts\python.exe scheduled_task.py --now
echo.
echo 任务执行完成
pause