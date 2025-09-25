#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
微信公众号爬虫 - 登录模块
=======================

使用 Playwright 自动打开浏览器，实现扫码登录并获取登录信息。

主要功能:
    1. 自动登录 - 启动浏览器并打开登录页面
    2. Token获取 - 提取访问token
    3. Cookie管理 - 获取和格式化cookie

版本: 2.0
"""

import json
import os
import random
import time
import re
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
import requests

# 导入日志模块
from spider.log.utils import logger

# 配置常量
CACHE_FILE = 'wechat_cache.json'
# Token/Cookie 最大有效时长（小时）
MAX_TOKEN_AGE_HOURS = 90


class WeChatSpiderLogin:
    """微信公众号登录管理器"""

    def __init__(self, cache_file=CACHE_FILE):
        """
        初始化登录管理器
        
        Args:
            cache_file (str): 缓存文件路径
        """
        self.token = None
        self.cookies = None
        self.cache_file = cache_file
        # 缓存写入时间（时间戳，秒）
        self.cache_timestamp = None

    def login(self):
        """
        使用 Playwright 登录微信公众号平台
        
        Returns:
            bool: 登录是否成功
        """
        logger.info("\n" + "="*60)
        logger.info("开始登录微信公众号平台...")
        logger.info("="*60)
        
        try:
            with sync_playwright() as p:
                # 启动浏览器
                logger.info("正在启动浏览器...")
                browser = p.chromium.launch(
                    headless=False,
                    args=[
                        '--start-maximized',  # 最大化窗口，更容易引起注意
                        '--no-proxy-server',  # 禁用代理服务器
                        '--disable-proxy',    # 禁用代理
                        '--proxy-server=direct://',  # 直接连接，绕过代理
                        '--proxy-bypass-list=*'      # 绕过所有代理
                    ],
                    # 新增：指定浏览器路径，可以避免因网络问题导致的启动失败
                    executable_path=p.chromium.executable_path
                )
                context = browser.new_context(
                    # 禁用浏览器级别的代理
                    proxy=None
                )
                page = context.new_page()
                
                # 访问微信公众号平台
                logger.info("正在访问微信公众号平台...")
                page.goto('https://mp.weixin.qq.com/')
                logger.success("页面加载完成")
                
                logger.info("请在浏览器窗口中扫码登录...")
                logger.warning("⚠️ 请勿关闭浏览器窗口！系统将等待您扫码登录...")
                logger.info("💡 提示：请使用微信扫描页面上的二维码")
                
                # 定期提醒功能
                import threading
                reminder_stop = threading.Event()
                
                def reminder():
                    """定期提醒用户扫码"""
                    count = 0
                    while not reminder_stop.is_set():
                        # 每30秒提醒一次
                        if reminder_stop.wait(30):
                            break
                        count += 1
                        elapsed_minutes = count * 0.5
                        logger.warning(f"⏰ 提醒：已等待 {elapsed_minutes:.1f} 分钟，请尽快扫码登录！")
                        logger.info("💡 如果二维码已过期，请刷新浏览器页面获取新的二维码")
                        
                        # 每5分钟（10次提醒）后给出更强烈的提醒
                        if count % 10 == 0:
                            logger.error(f"⚠️⚠️⚠️ 重要提醒：已等待 {elapsed_minutes:.0f} 分钟！")
                            logger.error("请立即在浏览器窗口中扫码登录，否则爬虫无法继续运行！")
                            logger.info("如需取消，请按 Ctrl+C 终止程序")
                
                # 启动提醒线程
                reminder_thread = threading.Thread(target=reminder, daemon=True)
                reminder_thread.start()

                # 无限等待登录成功（移除超时限制）
                logger.info("系统将持续等待，直到您完成扫码登录...")
                
                # 使用循环检查，而不是单次等待
                while True:
                    try:
                        # 每次等待60秒检查一次
                        page.wait_for_url(lambda url: 'token=' in url, timeout=60000)
                        # 如果成功，跳出循环
                        break
                    except:
                        # 超时后继续等待
                        # 检查页面是否还存在
                        try:
                            page.title()  # 尝试获取标题，测试页面是否还活着
                        except:
                            logger.error("浏览器窗口已关闭，登录失败")
                            reminder_stop.set()
                            return False
                        continue
                
                # 停止提醒线程
                reminder_stop.set()
                
                # 提取token
                current_url = page.url
                logger.success("检测到登录成功！正在获取登录信息...")
                
                token_match = re.search(r'token=(\d+)', current_url)
                if token_match:
                    self.token = token_match.group(1)
                    logger.success(f"Token获取成功: {self.token}")
                else:
                    logger.error("无法从URL中提取token")
                    browser.close()
                    return False

                # 获取cookies
                cookies = page.context.cookies()
                self.cookies = {cookie['name']: cookie['value'] for cookie in cookies}
                logger.success(f"Cookies获取成功，共{len(self.cookies)}个")
                
                # 保存到缓存
                if self.save_cache():
                    logger.success("登录信息已保存到缓存")
                
                browser.close()
                logger.success("登录完成！")
                return True
                
        except Exception as e:
            logger.error(f"登录过程中出现错误: {e}")
            
            # 根据错误类型提供具体的解决建议
            error_str = str(e).lower()
            if 'proxy' in error_str or 'err_proxy' in error_str:
                logger.error("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                logger.error("❌ 网络代理错误")
                logger.error("建议解决方案：")
                logger.error("1. 关闭系统代理：Windows设置 -> 网络和Internet -> 代理 -> 关闭")
                logger.error("2. 关闭VPN软件（如有）")
                logger.error("3. 检查防火墙设置")
                logger.error("4. 重启网络适配器")
                logger.error("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            elif 'timeout' in error_str:
                logger.error("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                logger.error("⏰ 网络超时错误")
                logger.error("建议解决方案：")
                logger.error("1. 检查网络连接是否稳定")
                logger.error("2. 切换到更稳定的网络环境")
                logger.error("3. 重新运行程序")
                logger.error("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            elif 'browser' in error_str:
                logger.error("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                logger.error("🌐 浏览器启动失败")
                logger.error("建议解决方案：")
                logger.error("1. 确保已安装 playwright: pip install playwright")
                logger.error("2. 安装浏览器: playwright install chromium")
                logger.error("3. 重启计算机后重试")
                logger.error("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            else:
                logger.error("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                logger.error("❓ 未知错误")
                logger.error("建议解决方案：")
                logger.error("1. 检查网络连接")
                logger.error("2. 重启程序")
                logger.error("3. 如问题持续，请联系技术支持")
                logger.error("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
            return False

    def save_cache(self):
        """保存token和cookies到缓存文件"""
        if self.token and self.cookies:
            cache_data = {
                'token': self.token,
                'cookies': self.cookies,
                'timestamp': datetime.now().timestamp()
            }
            try:
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
                logger.success(f"登录信息已保存到缓存文件 {self.cache_file}")
                return True
            except Exception as e:
                logger.error(f"保存缓存失败: {e}")
                return False
        return False

    def load_cache(self):
        """从缓存文件加载token和cookies"""
        if not os.path.exists(self.cache_file):
            logger.info("缓存文件不存在，需要重新登录")
            return False
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # 检查缓存时间
            cache_time = cache_data.get('timestamp', 0)
            current_time = datetime.now().timestamp()
            time_diff = (current_time - cache_time) / 3600  # 转换为小时
            self.cache_timestamp = cache_time

            # 超过设定的最大有效期则强制重新登录
            if time_diff >= MAX_TOKEN_AGE_HOURS:
                logger.warning(f"登录已超过{MAX_TOKEN_AGE_HOURS}小时（{time_diff:.1f}小时），需要重新登录")
                return False
            
            self.token = cache_data['token']
            self.cookies = cache_data['cookies']
            logger.info(f"从缓存加载登录信息（{time_diff:.1f}小时前保存）")
            return True
            
        except Exception as e:
            logger.error(f"读取缓存失败: {e}，需要重新登录")
            return False

    def validate_cache(self):
        """验证缓存的登录信息是否有效"""
        if not self.token or not self.cookies:
            if not self.load_cache():
                return False
        
        # 再次检查时间戴是否超过90小时
        if self.cache_timestamp:
            current_time = datetime.now().timestamp()
            time_diff = (current_time - self.cache_timestamp) / 3600
            if time_diff >= MAX_TOKEN_AGE_HOURS:
                logger.warning(f"登录信息已超过{MAX_TOKEN_AGE_HOURS}小时（{time_diff:.1f}小时），需要重新登录")
                logger.warning("↓↓↓ 请扫码重新登录以继续爬取 ↓↓↓")
                return False
        
        try:
            # 构造验证请求
            headers = self.get_headers()
            if not headers:
                return False
            
            # 测试请求一个简单的API来验证登录状态
            test_url = f"https://mp.weixin.qq.com/cgi-bin/searchbiz?action=search_biz&begin=0&count=5&query=test&token={self.token}&lang=zh_CN&f=json&ajax=1"
            
            response = requests.get(test_url, headers=headers, timeout=30, proxies={})
            
            # 检查响应状态
            if response.status_code == 200:
                data = response.json()
                base_resp = data.get('base_resp', {}) if isinstance(data, dict) else {}
                ret = base_resp.get('ret', None)
                err_msg = base_resp.get('err_msg') or base_resp.get('errmsg')

                # 仅当 ret==0 时认为会话有效，其他情况（含200003 invalid session、200013未登录等）均视为无效
                if ret == 0:
                    logger.success("缓存的登录信息验证有效")
                    return True
                else:
                    logger.warning(f"缓存登录无效: ret={ret}, err={err_msg}")
                    return False
            
            logger.warning("缓存的登录信息已失效")
            return False
            
        except Exception as e:
            logger.warning(f"验证缓存登录信息时出错: {e}")
            return False

    def is_logged_in(self):
        """
        检查是否已登录
        
        Returns:
            bool: 是否已登录
        """
        # 首先检查是否有token和cookies
        if not self.token or not self.cookies:
            # 尝试从缓存加载
            if not self.load_cache():
                return False
        
        # 验证缓存的有效性
        return self.validate_cache()

    def check_login_status(self):
        """
        检查登录状态
        
        Returns:
            dict: 登录状态信息
        """
        if self.is_logged_in():
            return {
                'logged_in': True,
                'token': self.token,
                'cache_file': self.cache_file,
                'cookies_count': len(self.cookies) if self.cookies else 0
            }
        else:
            return {
                'logged_in': False,
                'token': None,
                'cache_file': self.cache_file,
                'cookies_count': 0
            }

    def get_token(self):
        """
        获取token
        
        Returns:
            str: token字符串，如果未登录返回None
        """
        if not self.token and not self.load_cache():
            return None
        return self.token

    def get_cookies(self):
        """
        获取cookies字典
        
        Returns:
            dict: cookies字典，如果未登录返回None
        """
        if not self.cookies and not self.load_cache():
            return None
        return self.cookies

    def get_cookie_string(self):
        """
        获取cookie字符串格式
        
        Returns:
            str: cookie字符串，如果未登录返回None
        """
        cookies = self.get_cookies()
        if not cookies:
            return None
        
        cookie_string = '; '.join([f"{key}={value}" for key, value in cookies.items()])
        return cookie_string

    def get_headers(self):
        """
        获取标准的HTTP请求头
        
        Returns:
            dict: 包含cookie和user-agent的请求头，如果未登录返回None
        """
        import random
        
        cookie_string = self.get_cookie_string()
        if not cookie_string:
            return None
        
        # 随机选择一个现代的User-Agent
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        ]
        
        return {
            "cookie": cookie_string,
            "user-agent": random.choice(user_agents),
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
            "accept-encoding": "gzip, deflate, br",
            "referer": "https://mp.weixin.qq.com/",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "x-requested-with": "XMLHttpRequest"
        }


# 便捷函数
def quick_login():
    """
    快速登录函数
    
    Returns:
        tuple: (token, cookies, headers) 如果登录成功，否则返回 (None, None, None)
    """
    login_manager = WeChatSpiderLogin()
    if login_manager.login():
        return (
            login_manager.get_token(),
            login_manager.get_cookies(),
            login_manager.get_headers()
        )
    return (None, None, None)


def check_login():
    """
    检查登录状态的便捷函数
    
    Returns:
        dict: 登录状态信息
    """
    login_manager = WeChatSpiderLogin()
    return login_manager.check_login_status()