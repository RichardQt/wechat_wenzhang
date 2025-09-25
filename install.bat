@echo off
echo ===================================
echo 微信公众号爬虫环境安装
echo ===================================
echo.

echo 正在安装Python依赖包...
pip install -r requirements.txt

echo.
echo 正在安装Playwright浏览器...
playwright install chromium

echo.
echo ===================================
echo 安装完成！
echo.
echo 使用说明：
echo 1. 首次运行前，请确保MySQL数据库已启动
echo 2. 运行 python main.py login 进行登录
echo 3. 运行 python main.py db-test 测试数据库连接
echo 4. 运行 python main.py crawl 开始爬取所有公众号
echo 5. 运行 python main.py test --account "公众号名称" 测试单个公众号
echo ===================================
pause
