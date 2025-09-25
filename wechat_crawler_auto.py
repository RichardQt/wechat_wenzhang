#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
微信公众号自动爬虫
=================

自动登录、爬取文章并保存到MySQL数据库
"""

import requests
import json
import time
import random
import os
import ssl
import urllib3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

from spider.log.utils import logger
from auto_login import AutoLogin
from database import DatabaseManager
from get_cookie import extract_article_content_from_html

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 禁用代理
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'
# 清除可能存在的代理设置
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
    if proxy_var in os.environ:
        del os.environ[proxy_var]

class WeChatCrawlerAuto:
    """微信公众号自动爬虫"""
    
    def __init__(self):
        """初始化爬虫"""
        self.auto_login = AutoLogin()
        self.db = DatabaseManager()
        self.token = None
        self.cookie_string = None
        self.headers = None
        self.accounts = []
        self.login_time = None  # 记录登录时间
        
    def initialize(self):
        """初始化爬虫，包括登录和数据库连接"""
        logger.info("="*60)
        logger.info("初始化微信公众号爬虫")
        logger.info("="*60)
        
        # 确保登录
        self.token, self.cookie_string, self.headers = self.auto_login.ensure_login()
        if not self.token:
            logger.error("无法登录，爬虫初始化失败")
            return False
        self.login_time = datetime.now()  # 记录登录时间
        
        # 加载公众号列表
        self.accounts = self.auto_login.update_accounts_in_config()
        if not self.accounts:
            logger.error("没有要爬取的公众号")
            return False
        
        # 连接数据库
        if not self.db.connect():
            logger.error("数据库连接失败")
            return False
        
        logger.success("爬虫初始化成功")
        return True
    
    def check_and_refresh_login(self) -> bool:
        """
        检查登录状态，如果超过配置的小时数则自动重新登录
        
        Returns:
            bool: 登录状态是否有效
        """
        if self.login_time:
            elapsed_hours = (datetime.now() - self.login_time).total_seconds() / 3600
            
            # 从配置文件读取登录缓存时间，默认为89小时
            config = self.auto_login.load_config()
            login_cache_hours = config.get('login_cache_hours', 89)
            
            if elapsed_hours >= login_cache_hours:
                logger.warning(f"登录已超过{login_cache_hours}小时({elapsed_hours:.1f}小时)，开始自动重新登录...")
                logger.error("⚠️⚠️⚠️ Token即将过期！请立即扫码重新登录！⚠️⚠️⚠️")
                logger.info("★★★ 请在浏览器中扫码重新登录 ★★★")
                logger.info("🔔 浏览器窗口将保持打开状态，直到您完成登录...")
                self.token, self.cookie_string, self.headers = self.auto_login.ensure_login()
                if self.token:
                    self.login_time = datetime.now()
                    logger.success("✅ 重新登录成功，继续爬取")
                    return True
                else:
                    logger.error("❌ 重新登录失败")
                    return False
        return True
    
    def handle_api_error(self, response_data: dict, account_name: str = "") -> bool:
        """
        处理API响应错误，检查是否需要重新登录
        
        Args:
            response_data: API响应数据
            account_name: 当前处理的公众号名称
            
        Returns:
            bool: 是否需要重新登录并已成功重新登录
        """
        base_resp = response_data.get('base_resp', {}) if isinstance(response_data, dict) else {}
        ret = base_resp.get('ret', None)
        err_msg = base_resp.get('err_msg') or base_resp.get('errmsg')
        
        # 检测登录失效错误码
        if ret in [200003, 200013]:  # invalid session 或未登录
            logger.warning(f"检测到登录失效 (ret={ret}, err={err_msg})，尝试重新登录...")
            logger.error("⚠️⚠️⚠️ 登录失效！请立即扫码重新登录！⚠️⚠️⚠️")
            logger.info("★★★ 请在浏览器中扫码重新登录 ★★★")
            logger.info("🔔 浏览器窗口将保持打开状态，直到您完成登录...")
            self.token, self.cookie_string, self.headers = self.auto_login.ensure_login()
            if self.token:
                self.login_time = datetime.now()
                logger.success("✅ 重新登录成功，继续爬取")
                return True
            else:
                logger.error("❌ 重新登录失败，停止爬取")
                return False
        return False
    
    def search_account(self, account_name: str, retry_count: int = 0) -> Optional[str]:
        """
        搜索公众号并获取fakeid
        
        Args:
            account_name: 公众号名称
            retry_count: 重试次数
            
        Returns:
            str: fakeid，如果找不到返回None
        """
        # 检查是否需要刷新登录
        if not self.check_and_refresh_login():
            return None
            
        search_url = 'https://mp.weixin.qq.com/cgi-bin/searchbiz'
        params = {
            'action': 'search_biz',
            'token': self.token,
            'lang': 'zh_CN',
            'f': 'json',
            'ajax': '1',
            'random': random.random(),
            'query': account_name,
            'begin': 0,
            'count': '5'
        }
        
        try:
            response = requests.get(
                search_url, 
                headers=self.headers,
                params=params, 
                verify=False,
                timeout=30,
                proxies={}  # 禁用代理
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # 检查是否需要重新登录
                if self.handle_api_error(data, account_name) and retry_count < 1:
                    # 重新登录成功，重试搜索
                    return self.search_account(account_name, retry_count + 1)
                
                lists = data.get('list', [])
                
                if lists:
                    fakeid = lists[0].get('fakeid')
                    logger.info(f"找到公众号 [{account_name}]，fakeid: {fakeid}")
                    return fakeid
                else:
                    logger.warning(f"未找到公众号: {account_name}")
            else:
                logger.error(f"搜索公众号失败，状态码: {response.status_code}")
                
        except Exception as e:
            logger.error(f"搜索公众号时出错: {e}")
        
        return None
    
    def get_article_content(self, url: str) -> str:
        """
        获取文章全文内容
        
        Args:
            url: 文章URL
            
        Returns:
            str: 文章内容
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }
            
            response = requests.get(url, headers=headers, timeout=30, verify=False, proxies={})
            if response.status_code == 200:
                content_data = extract_article_content_from_html(response.text)
                return content_data.get('content', '获取内容失败')
            else:
                logger.warning(f"获取文章内容失败，状态码: {response.status_code}")
                return "获取内容失败"
                
        except Exception as e:
            logger.error(f"获取文章内容时出错: {e}")
            return "获取内容失败"
    
    def crawl_account_articles(self, account_name: str, fakeid: str, max_articles: int = 50, retry_count: int = 0) -> List[Dict]:
        """
        爬取某个公众号的文章
        
        Args:
            account_name: 公众号名称
            fakeid: 公众号的fakeid
            max_articles: 最大爬取文章数
            retry_count: 重试次数
            
        Returns:
            List[Dict]: 文章数据列表
        """
        articles = []
        logger.info(f"开始爬取公众号: {account_name}")
        
        # 获取配置参数
        config = self.auto_login.load_config()
        crawl_days = config.get('crawl_days', 7)  # 包含今天至当前时刻 + 前 N 个完整自然日
        article_interval = config.get('article_interval', [2, 5])  # 文章间隔时间
        
        # 计算时间范围：从今天00:00往前推 N 天（完整自然日），再加上今天至当前时刻
        now = datetime.now()
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_time = start_of_today - timedelta(days=crawl_days)
        start_timestamp = int(start_time.timestamp())
        logger.info(f"将爬取从 {start_time.strftime('%Y-%m-%d %H:%M:%S')} 至今的文章（包含今天至当前时间 + 前 {crawl_days} 个完整自然日）")
        
        for begin in range(0, max_articles, 5):
            # 每批次前检查是否需要刷新登录
            if not self.check_and_refresh_login():
                logger.error("登录失效且无法重新登录，停止爬取")
                break
                
            logger.info(f"正在获取第 {begin+1} 到 {min(begin+5, max_articles)} 篇文章...")
            
            # 构建请求URL
            url = f'https://mp.weixin.qq.com/cgi-bin/appmsg'
            params = {
                'token': self.token,
                'lang': 'zh_CN',
                'f': 'json',
                'ajax': '1',
                'random': random.random(),
                'action': 'list_ex',
                'begin': begin,
                'count': 5,
                'query': '',
                'fakeid': fakeid,
                'type': '9'
            }
            
            try:
                response = requests.get(
                    url,
                    headers=self.headers,
                    params=params,
                    verify=False,
                    timeout=30,
                    proxies={}  # 禁用代理
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # 检查是否需要重新登录
                    if self.handle_api_error(data, account_name) and retry_count < 1:
                        # 重新登录成功，重新开始爬取这个公众号
                        return self.crawl_account_articles(account_name, fakeid, max_articles, retry_count + 1)
                    
                    app_msg_list = data.get('app_msg_list', [])
                    
                    if not app_msg_list:
                        logger.info("没有更多文章了")
                        break
                    
                    for item in app_msg_list:
                        # 检查文章时间
                        create_time = item.get('create_time', 0)
                        if create_time < start_timestamp:
                            logger.info("文章发布时间早于配置的起始时间，停止爬取更早的文章")
                            return articles  # 停止爬取更早的文章
                        
                        # 提取文章信息
                        article_data = {
                            'title': item.get('title', ''),
                            'url': item.get('link', ''),
                            'publish_time': create_time,
                            'digest': item.get('digest', ''),
                            'cover': item.get('cover', ''),
                            'account_name': account_name
                        }
                        
                        # 获取文章全文
                        if article_data['url']:
                            logger.info(f"正在检查文章: {article_data['title']}")
                            
                            # 获取映射后的单位名称（用于标题去重）
                            unit_name = self.db.get_unit_name(account_name)
                            
                            # 检查文章URL是否已存在
                            if self.db.check_article_exists(article_data['url']):
                                logger.info(f"文章URL已存在，跳过: {article_data['title']}")
                                continue
                            
                            # 检查文章标题是否已存在
                            if article_data['title'] and self.db.check_article_exists_by_title(article_data['title'], unit_name):
                                logger.info(f"文章标题已存在，跳过: {article_data['title']} (单位: {unit_name})")
                                continue
                            
                            logger.info(f"正在获取文章全文: {article_data['title']}")
                            
                            content = self.get_article_content(article_data['url'])
                            article_data['content'] = content
                            
                            # 实时保存到数据库
                            if self.db.insert_article(article_data):
                                articles.append(article_data)
                                logger.success(f"文章已保存: {article_data['title']}")
                            
                            # 使用配置的文章间隔时间
                            delay = random.uniform(article_interval[0], article_interval[1])
                            logger.debug(f"等待 {delay:.1f} 秒后继续...")
                            time.sleep(delay)
                        
                else:
                    logger.error(f"获取文章列表失败，状态码: {response.status_code}")
                    break
                    
            except Exception as e:
                logger.error(f"获取文章列表时出错: {e}")
                break
            
            # 批次间延时
            time.sleep(random.uniform(3, 6))
        
        logger.info(f"公众号 [{account_name}] 爬取完成，共保存 {len(articles)} 篇新文章")
        return articles
    
    def crawl_all_accounts(self):
        """爬取所有公众号的文章"""
        total_articles = 0
        success_accounts = 0
        
        # 获取配置参数
        config = self.auto_login.load_config()
        account_interval = config.get('account_interval', [10, 20])  # 公众号间隔时间
        
        logger.info(f"开始爬取 {len(self.accounts)} 个公众号")
        
        for i, account_name in enumerate(self.accounts, 1):
            logger.info(f"\n处理第 {i}/{len(self.accounts)} 个公众号: {account_name}")
            
            # 搜索公众号获取fakeid
            fakeid = self.search_account(account_name)
            if not fakeid:
                logger.warning(f"跳过公众号: {account_name}")
                continue
            
            # 爬取文章
            articles = self.crawl_account_articles(
                account_name, 
                fakeid,
                max_articles=self.auto_login.load_config().get('max_articles_per_account', 50)
            )
            
            if articles:
                total_articles += len(articles)
                success_accounts += 1
            
            # 使用配置的公众号间隔时间
            if i < len(self.accounts):
                delay = random.uniform(account_interval[0], account_interval[1])
                logger.info(f"休息 {delay:.1f} 秒后继续下一个公众号...")
                time.sleep(delay)
        
        logger.info("="*60)
        logger.success(f"所有公众号爬取完成！")
        logger.info(f"成功爬取 {success_accounts}/{len(self.accounts)} 个公众号")
        logger.info(f"共保存 {total_articles} 篇新文章到数据库")
        
        # 记录本轮爬取完成时间
        if self.db.record_crawl_completion():
            logger.info("本轮爬取完成时间已记录到数据库")
        else:
            logger.warning("记录爬取完成时间失败")
        
        logger.info("="*60)
    
    def run(self):
        """运行爬虫"""
        try:
            # 初始化
            if not self.initialize():
                return
            
            # 开始爬取
            self.crawl_all_accounts()
            
        except KeyboardInterrupt:
            logger.warning("用户中断爬虫")
        except Exception as e:
            logger.error(f"爬虫运行出错: {e}")
        finally:
            # 清理资源
            self.db.disconnect()
            logger.info("爬虫已停止")
    
    def test_single_account(self, account_name: str):
        """
        测试爬取单个公众号
        
        Args:
            account_name: 公众号名称
        """
        try:
            # 初始化
            if not self.initialize():
                return
            
            logger.info(f"测试爬取公众号: {account_name}")
            
            # 搜索公众号
            fakeid = self.search_account(account_name)
            if not fakeid:
                logger.error(f"找不到公众号: {account_name}")
                return
            
            # 爬取文章（只爬取5篇用于测试）
            articles = self.crawl_account_articles(account_name, fakeid, max_articles=5)
            
            logger.success(f"测试完成，共爬取 {len(articles)} 篇文章")
            
        finally:
            self.db.disconnect()


def main():
    """主函数"""
    import sys
    
    crawler = WeChatCrawlerAuto()
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == 'test' and len(sys.argv) > 2:
            # 测试模式，爬取指定公众号
            crawler.test_single_account(sys.argv[2])
        elif sys.argv[1] == 'help':
            print("使用方法:")
            print("  python wechat_crawler_auto.py          # 爬取所有公众号")
            print("  python wechat_crawler_auto.py test 公众号名称  # 测试爬取单个公众号")
        else:
            print("未知参数，使用 'help' 查看帮助")
    else:
        # 正常运行，爬取所有公众号
        crawler.run()


if __name__ == "__main__":
    main()
