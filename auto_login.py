#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
自动登录模块
===========

整合login.py的功能，自动更新wechat_crawler_config.json
"""

import json
import os
from login import WeChatSpiderLogin
from spider.log.utils import logger

CONFIG_FILE = 'wechat_crawler_config.json'

class AutoLogin:
    """自动登录管理器"""
    
    def __init__(self):
        """初始化自动登录管理器"""
        self.login_manager = WeChatSpiderLogin()
        self.config_file = CONFIG_FILE
        
    def load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # 创建默认配置
            default_config = {
                'token': '',
                'cookie': '',
                'last_update': {},
                'max_articles_per_account': 50,
                'accounts': [],
                'crawl_days': 7,  # 爬取多少天内的文章
                'article_interval': [2, 5],  # 文章间隔时间[最小秒数, 最大秒数]
                'account_interval': [10, 20]  # 公众号间隔时间[最小秒数, 最大秒数]
            }
            self.save_config(default_config)
            return default_config
    
    def save_config(self, config):
        """保存配置文件"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        logger.info(f"配置已保存到 {self.config_file}")
    
    def update_login_info(self, token, cookie_string):
        """
        更新配置文件中的登录信息
        
        Args:
            token: 登录token
            cookie_string: cookie字符串
        """
        config = self.load_config()
        config['token'] = token
        config['cookie'] = cookie_string
        self.save_config(config)
        logger.success(f"登录信息已更新到 {self.config_file}")
    
    def ensure_login(self, max_retries=3):
        """
        确保登录状态有效，支持自动重试
        
        Args:
            max_retries: 最大重试次数
            
        Returns:
            tuple: (token, cookie_string, headers) 如果登录成功，否则返回 (None, None, None)
        """
        # 首先检查是否已登录
        if self.login_manager.is_logged_in():
            logger.success("使用缓存的登录信息")
            token = self.login_manager.get_token()
            cookie_string = self.login_manager.get_cookie_string()
            headers = self.login_manager.get_headers()
            
            # 更新配置文件
            self.update_login_info(token, cookie_string)
            
            return token, cookie_string, headers
        
        # 如果未登录或登录已失效，执行登录（支持重试）
        for retry_count in range(max_retries):
            logger.info("缓存登录信息无效或不存在，开始新的登录流程")
            if retry_count > 0:
                logger.warning(f"第 {retry_count + 1} 次尝试登录（剩余 {max_retries - retry_count - 1} 次）")
                logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                logger.info("💡 登录重试提示：")
                logger.info("• 确保网络连接稳定")
                logger.info("• 关闭所有VPN和代理软件")
                logger.info("• 检查防火墙设置")
                logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
            logger.info("★★★ 请在浏览器中扫码登录 ★★★")
            logger.warning("📢 正在打开浏览器窗口，请不要关闭它！")
            logger.info("🔔 系统将持续等待您完成扫码登录...")
            
            if self.login_manager.login():
                token = self.login_manager.get_token()
                cookie_string = self.login_manager.get_cookie_string()
                headers = self.login_manager.get_headers()
                
                # 更新配置文件
                self.update_login_info(token, cookie_string)
                
                logger.success("✅ 登录成功！继续执行爬虫任务...")
                return token, cookie_string, headers
            else:
                logger.error(f"第 {retry_count + 1} 次登录尝试失败")
                
                if retry_count < max_retries - 1:
                    import time
                    wait_time = 5 * (retry_count + 1)  # 递增等待时间
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    logger.error("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    logger.error("❌ 所有登录尝试均失败")
                    logger.error("建议解决方案：")
                    logger.error("1. 检查网络连接是否正常")
                    logger.error("2. 确认防火墙和代理设置")
                    logger.error("3. 重启程序和网络")
                    logger.error("4. 联系技术支持")
                    logger.error("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        logger.error("登录失败")
        return None, None, None
    
    def get_accounts_from_file(self, accounts_file='accounts.txt'):
        """
        从accounts.txt文件读取公众号列表
        
        Args:
            accounts_file: 账号列表文件路径
            
        Returns:
            list: 公众号名称列表
        """
        accounts = []
        if os.path.exists(accounts_file):
            with open(accounts_file, 'r', encoding='utf-8') as f:
                for line in f:
                    account = line.strip()
                    if account and not account.startswith('#'):  # 忽略空行和注释
                        accounts.append(account)
            logger.info(f"从 {accounts_file} 加载了 {len(accounts)} 个公众号")
        else:
            logger.warning(f"账号文件 {accounts_file} 不存在")
        
        return accounts
    
    def update_accounts_in_config(self):
        """更新配置文件中的公众号列表"""
        accounts = self.get_accounts_from_file()
        if accounts:
            config = self.load_config()
            config['accounts'] = accounts
            self.save_config(config)
            logger.success(f"已更新配置文件中的公众号列表，共 {len(accounts)} 个")
        return accounts


def test_auto_login():
    """测试自动登录功能"""
    auto_login = AutoLogin()
    
    # 确保登录
    token, cookie_string, headers = auto_login.ensure_login()
    
    if token:
        logger.success(f"登录成功，Token: {token[:20]}...")
        logger.info(f"Cookie长度: {len(cookie_string) if cookie_string else 0}")
        
        # 更新公众号列表
        accounts = auto_login.update_accounts_in_config()
        logger.info(f"公众号列表: {accounts[:5]}..." if len(accounts) > 5 else f"公众号列表: {accounts}")
    else:
        logger.error("登录失败，请检查网络或重试")


if __name__ == "__main__":
    test_auto_login()
